from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from django.contrib.auth.models import User
from django.db.models import Avg, Count
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes

from .models import Person, AnalysisSession, EmotionRecord, PostureRecord, BehaviorAlert
from .serializers import (
    UserRegistrationSerializer, UserLoginSerializer, UserSerializer,
    ChangePasswordSerializer, TokenResponseSerializer,
    PersonSerializer, PersonCreateSerializer, PersonListSerializer,
    AnalysisSessionSerializer, AnalysisSessionListSerializer, AnalysisSessionDetailSerializer,
    BehaviorAlertSerializer, BehaviorAlertListSerializer,
    BehaviorReportSerializer, RecommendationSerializer
)


# ============================================================
# VISTAS DE AUTENTICACIÓN
# ============================================================

@extend_schema(
    tags=['Auth'],
    summary='Registrar nuevo usuario',
    description='Crea una nueva cuenta de usuario y devuelve tokens JWT.',
    request=UserRegistrationSerializer,
    responses={201: TokenResponseSerializer}
)
class RegisterView(generics.CreateAPIView):
    """
    Registro de nuevos usuarios.
    
    Crea una cuenta y devuelve tokens de acceso y refresh.
    """
    queryset = User.objects.all()
    permission_classes = (permissions.AllowAny,)
    serializer_class = UserRegistrationSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'user': UserSerializer(user).data,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'message': 'Usuario registrado exitosamente.'
        }, status=status.HTTP_201_CREATED)


@extend_schema(
    tags=['Auth'],
    summary='Iniciar sesión',
    description='Autentica un usuario y devuelve tokens JWT.',
    request=UserLoginSerializer,
    responses={200: TokenResponseSerializer}
)
class LoginView(APIView):
    """
    Login de usuarios.
    
    Autentica credenciales y devuelve tokens JWT.
    """
    permission_classes = (permissions.AllowAny,)
    serializer_class = UserLoginSerializer
    
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'user': UserSerializer(user).data,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        })


@extend_schema(
    tags=['Auth'],
    summary='Cerrar sesión',
    description='Invalida el refresh token actual.',
)
class LogoutView(APIView):
    """
    Logout de usuarios.
    
    Invalida el refresh token para cerrar sesión.
    """
    permission_classes = (permissions.IsAuthenticated,)
    
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            return Response({'message': 'Sesión cerrada exitosamente.'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    tags=['Auth'],
    summary='Obtener perfil del usuario',
    description='Devuelve información del usuario autenticado.',
    responses={200: UserSerializer}
)
class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    Perfil del usuario autenticado.
    
    GET: Obtiene información del usuario.
    PUT/PATCH: Actualiza información del usuario.
    """
    serializer_class = UserSerializer
    permission_classes = (permissions.IsAuthenticated,)
    
    def get_object(self):
        return self.request.user


@extend_schema(
    tags=['Auth'],
    summary='Cambiar contraseña',
    description='Cambia la contraseña del usuario autenticado.',
    request=ChangePasswordSerializer,
)
class ChangePasswordView(APIView):
    """Cambio de contraseña del usuario autenticado."""
    permission_classes = (permissions.IsAuthenticated,)
    
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        if not user.check_password(serializer.validated_data['old_password']):
            return Response(
                {'old_password': 'Contraseña actual incorrecta.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        
        return Response({'message': 'Contraseña cambiada exitosamente.'})


# ============================================================
# VISTAS DE PERSONAS
# ============================================================

@extend_schema_view(
    list=extend_schema(
        tags=['Persons'],
        summary='Listar personas',
        description='Obtiene lista paginada de todas las personas registradas.'
    ),
    create=extend_schema(
        tags=['Persons'],
        summary='Crear persona',
        description='Registra una nueva persona para análisis.'
    ),
    retrieve=extend_schema(
        tags=['Persons'],
        summary='Obtener persona',
        description='Obtiene detalles de una persona específica.'
    ),
    update=extend_schema(
        tags=['Persons'],
        summary='Actualizar persona',
        description='Actualiza todos los campos de una persona.'
    ),
    partial_update=extend_schema(
        tags=['Persons'],
        summary='Actualizar parcialmente',
        description='Actualiza campos específicos de una persona.'
    ),
    destroy=extend_schema(
        tags=['Persons'],
        summary='Eliminar persona',
        description='Elimina una persona y todos sus datos asociados.'
    ),
)
class PersonViewSet(generics.ListCreateAPIView):
    """
    CRUD de Personas.
    
    Gestiona los perfiles de personas para análisis emocional.
    """
    queryset = Person.objects.all().order_by('-date_joined')
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return PersonCreateSerializer
        return PersonListSerializer


class PersonDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Detalle, actualización y eliminación de persona."""
    queryset = Person.objects.all()
    serializer_class = PersonSerializer


# ============================================================
# VISTAS DE SESIONES
# ============================================================

@extend_schema(
    tags=['Sessions'],
    summary='Listar sesiones de una persona',
    description='Obtiene todas las sesiones de análisis de una persona.',
    parameters=[
        OpenApiParameter(
            name='person_id',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description='ID de la persona'
        )
    ]
)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def person_sessions(request, person_id):
    """Lista todas las sesiones de una persona."""
    try:
        person = Person.objects.get(id=person_id)
        sessions = AnalysisSession.objects.filter(person=person).order_by('-started_at')
        serializer = AnalysisSessionListSerializer(sessions, many=True)
        
        return Response({
            'person': PersonListSerializer(person).data,
            'total_sessions': sessions.count(),
            'sessions': serializer.data
        })
    except Person.DoesNotExist:
        return Response({'error': 'Persona no encontrada'}, status=status.HTTP_404_NOT_FOUND)


@extend_schema(
    tags=['Sessions'],
    summary='Detalle de sesión',
    description='Obtiene información completa de una sesión con emociones, posturas y alertas.',
)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def session_detail(request, session_id):
    """Obtiene detalles completos de una sesión."""
    try:
        session = AnalysisSession.objects.get(id=session_id)
        serializer = AnalysisSessionDetailSerializer(session)
        return Response(serializer.data)
    except AnalysisSession.DoesNotExist:
        return Response({'error': 'Sesión no encontrada'}, status=status.HTTP_404_NOT_FOUND)


@extend_schema(
    tags=['Sessions'],
    summary='Listar todas las sesiones',
    description='Obtiene lista paginada de todas las sesiones de análisis.',
)
class SessionListView(generics.ListAPIView):
    """Lista todas las sesiones de análisis."""
    queryset = AnalysisSession.objects.all().order_by('-started_at')
    serializer_class = AnalysisSessionListSerializer


# ============================================================
# VISTAS DE ALERTAS
# ============================================================

@extend_schema(
    tags=['Alerts'],
    summary='Alertas de una persona',
    description='Obtiene todas las alertas de comportamiento de una persona.',
)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def person_alerts(request, person_id):
    """Lista todas las alertas de una persona."""
    try:
        person = Person.objects.get(id=person_id)
        alerts = BehaviorAlert.objects.filter(session__person=person).order_by('-created_at')
        serializer = BehaviorAlertListSerializer(alerts, many=True)
        
        return Response({
            'person_id': person_id,
            'person_name': f"{person.first_name} {person.last_name}",
            'total_alerts': alerts.count(),
            'unreviewed_count': alerts.filter(is_reviewed=False).count(),
            'alerts': serializer.data
        })
    except Person.DoesNotExist:
        return Response({'error': 'Persona no encontrada'}, status=status.HTTP_404_NOT_FOUND)


@extend_schema(
    tags=['Alerts'],
    summary='Listar todas las alertas',
    description='Obtiene lista paginada de todas las alertas del sistema.',
)
class AlertListView(generics.ListAPIView):
    """Lista todas las alertas del sistema."""
    queryset = BehaviorAlert.objects.all().order_by('-created_at')
    serializer_class = BehaviorAlertSerializer


@extend_schema(
    tags=['Alerts'],
    summary='Marcar alerta como revisada',
    description='Actualiza el estado de revisión de una alerta.',
)
@api_view(['PATCH'])
@permission_classes([permissions.IsAuthenticated])
def mark_alert_reviewed(request, alert_id):
    """Marca una alerta como revisada."""
    try:
        alert = BehaviorAlert.objects.get(id=alert_id)
        alert.is_reviewed = True
        alert.save()
        return Response({'message': 'Alerta marcada como revisada.'})
    except BehaviorAlert.DoesNotExist:
        return Response({'error': 'Alerta no encontrada'}, status=status.HTTP_404_NOT_FOUND)


# ============================================================
# VISTAS DE REPORTES
# ============================================================

@extend_schema(
    tags=['Reports'],
    summary='Reporte de comportamiento',
    description='''
    Genera un reporte completo del comportamiento de una persona.
    
    Incluye:
    - Promedio de emociones
    - Distribución de estados
    - Resumen de alertas
    - Tendencia general
    - Recomendaciones
    ''',
    responses={200: BehaviorReportSerializer}
)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def behavior_report(request, person_id):
    """Genera reporte de comportamiento de una persona."""
    try:
        person = Person.objects.get(id=person_id)
        sessions = AnalysisSession.objects.filter(person=person)
        
        if not sessions.exists():
            return Response({
                'person': PersonListSerializer(person).data,
                'message': 'No hay sesiones registradas para generar reporte.'
            })
        
        # Calcular promedios
        total_sessions = sessions.count()
        avg_emotions = sessions.aggregate(
            happy=Avg('happy_pct'),
            sad=Avg('sad_pct'),
            angry=Avg('angry_pct'),
            fear=Avg('fear_pct'),
            surprise=Avg('surprise_pct'),
            disgust=Avg('disgust_pct'),
            neutral=Avg('neutral_pct'),
        )
        
        # Distribución de estados
        state_counts = dict(sessions.values_list('overall_state').annotate(count=Count('id')))
        
        # Resumen de alertas
        alerts = BehaviorAlert.objects.filter(session__person=person)
        alert_counts = dict(alerts.values_list('alert_type').annotate(count=Count('id')))
        
        # Determinar tendencia
        avg_sad = avg_emotions.get('sad') or 0
        avg_fear = avg_emotions.get('fear') or 0
        
        if avg_sad > 50 or avg_fear > 40:
            tendency = 'atencion_urgente'
        elif avg_sad > 35 or avg_fear > 25:
            tendency = 'requiere_atencion'
        else:
            tendency = 'estable'
        
        # Generar recomendación
        recommendation = get_recommendation(tendency, avg_sad, avg_fear)
        
        return Response({
            'person': PersonListSerializer(person).data,
            'total_sessions': total_sessions,
            'average_emotions': {k: round(v or 0, 2) for k, v in avg_emotions.items()},
            'state_distribution': state_counts,
            'alert_summary': alert_counts,
            'overall_tendency': tendency,
            'recommendation': recommendation
        })
        
    except Person.DoesNotExist:
        return Response({'error': 'Persona no encontrada'}, status=status.HTTP_404_NOT_FOUND)


def get_recommendation(tendency, sad_pct, fear_pct):
    """Genera recomendaciones basadas en el análisis."""
    if tendency == 'atencion_urgente':
        return {
            'level': 'urgente',
            'message': 'Se recomienda consulta con especialista de salud mental.',
            'suggestions': [
                'Buscar apoyo profesional inmediato',
                'Actividades de relajación guiada',
                'Monitoreo frecuente y seguimiento',
                'Comunicación con familia o tutores'
            ]
        }
    elif tendency == 'requiere_atencion':
        return {
            'level': 'moderado',
            'message': 'Se detectan patrones que requieren seguimiento.',
            'suggestions': [
                'Actividades recreativas regulares',
                'Ejercicio físico diario',
                'Técnicas de respiración y mindfulness',
                'Seguimiento semanal'
            ]
        }
    else:
        return {
            'level': 'normal',
            'message': 'Estado emocional dentro de parámetros normales.',
            'suggestions': [
                'Mantener rutinas saludables',
                'Continuar monitoreo regular',
                'Fomentar actividades positivas'
            ]
        }


# ============================================================
# VISTAS DE ESTADÍSTICAS GENERALES
# ============================================================

@extend_schema(
    tags=['Reports'],
    summary='Dashboard general',
    description='Obtiene estadísticas generales del sistema.',
)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def dashboard_stats(request):
    """Estadísticas generales del dashboard."""
    total_persons = Person.objects.count()
    total_sessions = AnalysisSession.objects.count()
    total_alerts = BehaviorAlert.objects.count()
    unreviewed_alerts = BehaviorAlert.objects.filter(is_reviewed=False).count()
    
    # Sesiones recientes
    recent_sessions = AnalysisSession.objects.order_by('-started_at')[:5]
    
    # Alertas recientes
    recent_alerts = BehaviorAlert.objects.filter(is_reviewed=False).order_by('-created_at')[:5]
    
    # Distribución de estados
    state_distribution = dict(
        AnalysisSession.objects.values_list('overall_state').annotate(count=Count('id'))
    )
    
    return Response({
        'totals': {
            'persons': total_persons,
            'sessions': total_sessions,
            'alerts': total_alerts,
            'unreviewed_alerts': unreviewed_alerts,
        },
        'state_distribution': state_distribution,
        'recent_sessions': AnalysisSessionListSerializer(recent_sessions, many=True).data,
        'recent_alerts': BehaviorAlertListSerializer(recent_alerts, many=True).data,
    })


# ============================================================
# ENDPOINT REST PARA ANÁLISIS DE IMAGEN
# ============================================================

# Variables globales para modelos (lazy loading)
_deepface_model = None
_yolo_model = None


def get_analysis_models():
    """Carga los modelos de ML de forma lazy"""
    global _deepface_model, _yolo_model
    
    if _deepface_model is None:
        import os
        os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
        os.environ['TF_FORCE_GPU_ALLOW_GROWTH'] = 'true'
        from deepface import DeepFace
        _deepface_model = DeepFace
    
    if _yolo_model is None:
        from ultralytics import YOLO
        _yolo_model = YOLO("yolov8n-pose.pt")
    
    return _deepface_model, _yolo_model


@extend_schema(
    tags=['Analysis'],
    summary='Analizar imagen',
    description='''
    Analiza una imagen enviada en base64 y devuelve:
    - Emoción dominante y scores
    - Detección de postura (cabeza baja, hombros encogidos, manos en cara)
    - Estado general
    
    **Ejemplo de request:**
    ```json
    {
        "image": "base64_encoded_image_data"
    }
    ```
    ''',
)
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def analyze_image(request):
    """
    Analiza una imagen y devuelve emociones y posturas.
    
    POST con JSON:
    {
        "image": "base64_encoded_image"
    }
    """
    import base64
    import numpy as np
    import cv2
    from django.utils import timezone
    
    try:
        image_data = request.data.get('image')
        
        if not image_data:
            return Response({
                'error': 'Se requiere el campo "image" con la imagen en base64'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Decodificar imagen base64
        try:
            # Remover prefijo data:image si existe
            if ',' in image_data:
                image_data = image_data.split(',')[1]
            
            image_bytes = base64.b64decode(image_data)
            nparr = np.frombuffer(image_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if frame is None:
                return Response({
                    'error': 'No se pudo decodificar la imagen. Verifica el formato base64.'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            return Response({
                'error': f'Error decodificando imagen: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Cargar modelos
        DeepFace, pose_model = get_analysis_models()
        
        result = {
            'emotion': None,
            'emotion_scores': {},
            'age': None,
            'gender': None,
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
                actions=['emotion', 'age', 'gender'],
                enforce_detection=False,
                detector_backend='opencv'
            )
            analysis = analysis[0] if isinstance(analysis, list) else analysis
            result['emotion'] = analysis.get('dominant_emotion')
            result['emotion_scores'] = analysis.get('emotion', {})
            result['age'] = analysis.get('age')
            result['gender'] = analysis.get('dominant_gender')
        except Exception as e:
            result['emotion_error'] = str(e)
        
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
        except Exception as e:
            result['posture_error'] = str(e)
        
        # 3. Determinar estado general
        if result['emotion'] in ['sad', 'fear', 'angry']:
            if result['head_down'] or result['hunched']:
                result['overall_state'] = 'anxious'
            else:
                result['overall_state'] = 'stressed'
        elif result['hands_on_face']:
            result['overall_state'] = 'nervous'
        
        return Response({
            'success': True,
            'analysis': result
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
