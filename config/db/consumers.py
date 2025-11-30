import json
import base64
import numpy as np
import cv2
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from .models import Person, AnalysisSession, EmotionRecord, PostureRecord, BehaviorAlert
from collections import Counter

# Importaciones para análisis (lazy loading para evitar cargar en cada conexión)
deepface_model = None
yolo_model = None


def get_models():
    """Carga los modelos de ML de forma lazy"""
    global deepface_model, yolo_model
    
    if deepface_model is None:
        import os
        os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
        from deepface import DeepFace
        deepface_model = DeepFace
    
    if yolo_model is None:
        from ultralytics import YOLO
        yolo_model = YOLO("yolov8n-pose.pt")
    
    return deepface_model, yolo_model


class EmotionAnalysisConsumer(AsyncWebsocketConsumer):
    """
    WebSocket Consumer para análisis emocional en tiempo real.
    
    Flutter envía frames de video codificados en base64.
    El servidor analiza y devuelve emociones/posturas en tiempo real.
    """
    
    async def connect(self):
        self.session = None
        self.person_id = self.scope['url_route']['kwargs'].get('person_id')
        self.emotion_history = []
        self.posture_history = []
        
        await self.accept()
        
        # Crear sesión de análisis
        if self.person_id:
            self.session = await self.create_session(self.person_id)
            await self.send(json.dumps({
                'type': 'session_started',
                'session_id': self.session.id if self.session else None,
                'message': 'Conexión establecida. Listo para análisis.'
            }))
    
    async def disconnect(self, close_code):
        # Finalizar sesión y calcular métricas
        if self.session:
            await self.finalize_session()
    
    async def receive(self, text_data):
        """Recibe frames de video en base64 desde Flutter"""
        try:
            data = json.loads(text_data)
            
            if data.get('type') == 'frame':
                # Decodificar imagen base64
                image_data = base64.b64decode(data['image'])
                nparr = np.frombuffer(image_data, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                
                if frame is not None:
                    # Analizar frame
                    result = await self.analyze_frame(frame)
                    
                    # Guardar en historial
                    if result['emotion']:
                        self.emotion_history.append(result['emotion'])
                    if any([result['head_down'], result['hunched'], result['hands_on_face']]):
                        self.posture_history.append({
                            'head_down': result['head_down'],
                            'hunched': result['hunched'],
                            'hands_on_face': result['hands_on_face']
                        })
                    
                    # Guardar en BD cada 10 frames
                    if len(self.emotion_history) % 10 == 0 and self.session:
                        await self.save_records(result)
                    
                    # Enviar resultado al cliente
                    await self.send(json.dumps({
                        'type': 'analysis_result',
                        **result
                    }))
            
            elif data.get('type') == 'get_metrics':
                # Cliente solicita métricas actuales
                metrics = self.calculate_metrics()
                await self.send(json.dumps({
                    'type': 'metrics',
                    **metrics
                }))
            
            elif data.get('type') == 'stop':
                # Cliente solicita detener análisis
                await self.finalize_session()
                await self.send(json.dumps({
                    'type': 'session_ended',
                    'metrics': self.calculate_metrics()
                }))
                await self.close()
                
        except Exception as e:
            await self.send(json.dumps({
                'type': 'error',
                'message': str(e)
            }))
    
    async def analyze_frame(self, frame):
        """Analiza un frame de video"""
        DeepFace, pose_model = get_models()
        
        result = {
            'emotion': None,
            'emotion_scores': {},
            'head_down': False,
            'hunched': False,
            'hands_on_face': False,
            'overall_state': 'normal',
            'timestamp': timezone.now().isoformat()
        }
        
        # Redimensionar para eficiencia
        small_frame = cv2.resize(frame, (320, 240))
        
        # 1. Análisis de emociones con DeepFace
        try:
            analysis = DeepFace.analyze(
                small_frame,
                actions=['emotion'],
                enforce_detection=False,
                detector_backend='opencv'
            )
            analysis = analysis[0] if isinstance(analysis, list) else analysis
            result['emotion'] = analysis['dominant_emotion']
            # Convertir float32 a float nativo de Python para JSON
            result['emotion_scores'] = {k: float(v) for k, v in analysis['emotion'].items()}
        except:
            pass
        
        # 2. Análisis de postura con YOLO
        try:
            pose_results = pose_model(frame, verbose=False)
            
            if pose_results[0].keypoints is not None:
                keypoints = pose_results[0].keypoints
                
                for person_idx in range(len(keypoints)):
                    xy = keypoints.xy[person_idx].cpu().numpy()
                    
                    nose = xy[0]
                    left_shoulder = xy[5]
                    right_shoulder = xy[6]
                    left_wrist = xy[9]
                    right_wrist = xy[10]
                    
                    # Cabeza abajo
                    if nose[0] > 0 and left_shoulder[0] > 0 and right_shoulder[0] > 0:
                        avg_shoulder_y = (left_shoulder[1] + right_shoulder[1]) / 2
                        if nose[1] > avg_shoulder_y:
                            result['head_down'] = True
                        
                        # Hombros encogidos
                        shoulder_distance = abs(left_shoulder[0] - right_shoulder[0])
                        if shoulder_distance < frame.shape[1] * 0.15:
                            result['hunched'] = True
                    
                    # Manos en cara
                    if left_wrist[0] > 0 and nose[0] > 0:
                        dist = np.sqrt((left_wrist[0] - nose[0])**2 + (left_wrist[1] - nose[1])**2)
                        if dist < 100:
                            result['hands_on_face'] = True
                    if right_wrist[0] > 0 and nose[0] > 0:
                        dist = np.sqrt((right_wrist[0] - nose[0])**2 + (right_wrist[1] - nose[1])**2)
                        if dist < 100:
                            result['hands_on_face'] = True
        except:
            pass
        
        # 3. Determinar estado general
        if result['emotion'] in ['sad', 'fear', 'angry']:
            if result['head_down'] or result['hunched']:
                result['overall_state'] = 'anxious'
            else:
                result['overall_state'] = 'stressed'
        elif result['hands_on_face']:
            result['overall_state'] = 'nervous'
        
        return result
    
    def calculate_metrics(self):
        """Calcula métricas acumuladas de la sesión"""
        if not self.emotion_history:
            return {
                'total_frames': 0,
                'emotion_percentages': {},
                'posture_counts': {
                    'head_down': 0,
                    'hunched': 0,
                    'hands_on_face': 0
                },
                'alerts': []
            }
        
        total = len(self.emotion_history)
        counts = Counter(self.emotion_history)
        
        emotion_pcts = {emo: (count / total) * 100 for emo, count in counts.items()}
        
        posture_counts = {
            'head_down': sum(1 for p in self.posture_history if p.get('head_down')),
            'hunched': sum(1 for p in self.posture_history if p.get('hunched')),
            'hands_on_face': sum(1 for p in self.posture_history if p.get('hands_on_face'))
        }
        
        # Generar alertas
        alerts = []
        if emotion_pcts.get('sad', 0) > 35:
            alerts.append({'type': 'high_sadness', 'message': 'Tristeza elevada detectada', 'severity': 'medium'})
        if emotion_pcts.get('fear', 0) > 25:
            alerts.append({'type': 'high_anxiety', 'message': 'Ansiedad elevada detectada', 'severity': 'medium'})
        if emotion_pcts.get('angry', 0) > 30:
            alerts.append({'type': 'high_anger', 'message': 'Irritabilidad elevada detectada', 'severity': 'medium'})
        if posture_counts['head_down'] > total * 0.3:
            alerts.append({'type': 'depressive_posture', 'message': 'Postura depresiva frecuente', 'severity': 'low'})
        
        return {
            'total_frames': total,
            'emotion_percentages': emotion_pcts,
            'posture_counts': posture_counts,
            'alerts': alerts
        }
    
    @database_sync_to_async
    def create_session(self, person_id):
        """Crea una nueva sesión de análisis"""
        try:
            person = Person.objects.get(id=person_id)
            session = AnalysisSession.objects.create(person=person)
            return session
        except Person.DoesNotExist:
            return None
    
    @database_sync_to_async
    def save_records(self, result):
        """Guarda registros en la base de datos"""
        if not self.session:
            return
        
        # Guardar emoción
        if result['emotion']:
            EmotionRecord.objects.create(
                session=self.session,
                dominant_emotion=result['emotion'],
                happy_score=result['emotion_scores'].get('happy', 0),
                sad_score=result['emotion_scores'].get('sad', 0),
                angry_score=result['emotion_scores'].get('angry', 0),
                fear_score=result['emotion_scores'].get('fear', 0),
                surprise_score=result['emotion_scores'].get('surprise', 0),
                disgust_score=result['emotion_scores'].get('disgust', 0),
                neutral_score=result['emotion_scores'].get('neutral', 0)
            )
        
        # Guardar postura
        if any([result['head_down'], result['hunched'], result['hands_on_face']]):
            PostureRecord.objects.create(
                session=self.session,
                head_down=result['head_down'],
                hunched_shoulders=result['hunched'],
                hands_on_face=result['hands_on_face']
            )
    
    @database_sync_to_async
    def finalize_session(self):
        """Finaliza la sesión y guarda métricas"""
        if not self.session:
            return
        
        metrics = self.calculate_metrics()
        
        self.session.ended_at = timezone.now()
        self.session.duration_seconds = (self.session.ended_at - self.session.started_at).total_seconds()
        
        # Guardar porcentajes
        self.session.happy_pct = metrics['emotion_percentages'].get('happy', 0)
        self.session.sad_pct = metrics['emotion_percentages'].get('sad', 0)
        self.session.angry_pct = metrics['emotion_percentages'].get('angry', 0)
        self.session.fear_pct = metrics['emotion_percentages'].get('fear', 0)
        self.session.surprise_pct = metrics['emotion_percentages'].get('surprise', 0)
        self.session.disgust_pct = metrics['emotion_percentages'].get('disgust', 0)
        self.session.neutral_pct = metrics['emotion_percentages'].get('neutral', 0)
        
        # Guardar conteos de postura
        self.session.head_down_count = metrics['posture_counts']['head_down']
        self.session.hunched_count = metrics['posture_counts']['hunched']
        self.session.hands_on_face_count = metrics['posture_counts']['hands_on_face']
        
        # Determinar estado general
        if metrics['emotion_percentages'].get('sad', 0) > 35:
            self.session.overall_state = 'sad'
        elif metrics['emotion_percentages'].get('fear', 0) > 25:
            self.session.overall_state = 'anxious'
        else:
            self.session.overall_state = 'stable'
        
        self.session.save()
        
        # Crear alertas
        for alert in metrics['alerts']:
            BehaviorAlert.objects.create(
                session=self.session,
                alert_type=alert['type'],
                severity=alert['severity'],
                message=alert['message']
            )
