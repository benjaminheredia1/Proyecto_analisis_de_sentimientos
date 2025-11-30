import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
os.environ['TF_FORCE_GPU_ALLOW_GROWTH'] = 'true'

import cv2
from deepface import DeepFace
from collections import Counter
from ultralytics import YOLO
import numpy as np
import tensorflow as tf

# Configurar GPU con crecimiento dinámico
gpus = tf.config.list_physical_devices('GPU')
if gpus:
    try:
        for gpu in gpus:
            tf.config.experimental.set_memory_growth(gpu, True)
        print(f"GPU detectada: {gpus[0].name}")
    except RuntimeError as e:
        print(f"Error GPU: {e}")

# ---- Configura cámara ----
cap = cv2.VideoCapture(0)
frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

# ---- Modelo YOLO Pose ----
pose_model = YOLO("yolov8n-pose.pt")

# ---- Historial de emociones ----
emotion_history = []

# ---- Loop principal ----
while True:
    ret, frame = cap.read()
    if not ret:
        break

    small_frame = cv2.resize(frame, (320, 240))  # Reducir para ahorrar memoria GPU

    # ---- 1️⃣ Emociones con DeepFace ----
    try:
        result = DeepFace.analyze(
            small_frame,
            actions=['emotion'],  # Solo emoción para reducir carga GPU
            enforce_detection=False,
            detector_backend='opencv'
        )
        result = result[0] if isinstance(result, list) else result
        emotion = result['dominant_emotion']
        emotion_scores = result['emotion']

        # Guardar en historial
        emotion_history.append({
            "emotion": emotion,
            "scores": emotion_scores,
            "time": cv2.getTickCount() / cv2.getTickFrequency()
        })
    except:
        emotion = None
        emotion_scores = None

    # ---- 2️⃣ Postura / Movimiento con YOLO Pose ----
    pose_results = pose_model(frame, verbose=False)
    annotated_frame = pose_results[0].plot()

    # Detectar posturas de ansiedad/tristeza
    posture_flag = False
    hands_on_face = False
    hunched = False
    
    if pose_results[0].keypoints is not None:
        keypoints = pose_results[0].keypoints
        
        # Iterar sobre cada persona detectada
        for person_idx in range(len(keypoints)):
            xy = keypoints.xy[person_idx].cpu().numpy()  # Convertir a CPU y NumPy
            
            # Keypoints: 0=nose, 5=left_shoulder, 6=right_shoulder, 9=left_wrist, 10=right_wrist
            nose = xy[0]
            left_shoulder = xy[5]
            right_shoulder = xy[6]
            left_wrist = xy[9]
            right_wrist = xy[10]
            
            # Verificar que los keypoints fueron detectados
            if nose[0] > 0 and left_shoulder[0] > 0 and right_shoulder[0] > 0:
                avg_shoulder_y = (left_shoulder[1] + right_shoulder[1]) / 2
                
                # Cabeza abajo (posible tristeza)
                if nose[1] > avg_shoulder_y:
                    posture_flag = True
                
                # Hombros encogidos (posible ansiedad)
                shoulder_distance = abs(left_shoulder[0] - right_shoulder[0])
                if shoulder_distance < frame_width * 0.15:
                    hunched = True
            
            # Manos cerca de la cara (posible ansiedad/nerviosismo)
            if left_wrist[0] > 0 and nose[0] > 0:
                dist_left = np.sqrt((left_wrist[0] - nose[0])**2 + (left_wrist[1] - nose[1])**2)
                if dist_left < 100:
                    hands_on_face = True
            if right_wrist[0] > 0 and nose[0] > 0:
                dist_right = np.sqrt((right_wrist[0] - nose[0])**2 + (right_wrist[1] - nose[1])**2)
                if dist_right < 100:
                    hands_on_face = True

    # ---- 3️⃣ Análisis de estado emocional ----
    estado = "Normal"
    color = (0, 255, 0)  # Verde
    
    if emotion in ['sad', 'fear', 'angry']:
        if posture_flag or hunched:
            estado = "Posible tristeza/ansiedad"
            color = (0, 0, 255)  # Rojo
        else:
            estado = f"Emoción: {emotion}"
            color = (0, 165, 255)  # Naranja
    
    if hands_on_face:
        estado = "Nerviosismo detectado"
        color = (0, 165, 255)

    # ---- 4️⃣ Mostrar información ----
    cv2.putText(annotated_frame, f"Estado: {estado}", (20, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
    if emotion:
        cv2.putText(annotated_frame, f"Emocion: {emotion}", (20, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    if posture_flag:
        cv2.putText(annotated_frame, "Cabeza baja", (20, 90),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
    if hunched:
        cv2.putText(annotated_frame, "Hombros encogidos", (20, 120),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
    if hands_on_face:
        cv2.putText(annotated_frame, "Manos en cara", (20, 150),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)

    cv2.imshow("Baymax Infantil - Analisis Emocional", annotated_frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()

# ---- 5️⃣ Análisis emocional acumulado ----
if emotion_history:
    total = len(emotion_history)
    counts = Counter([e["emotion"] for e in emotion_history])

    print("\n=== Porcentajes de emociones recogidas ===")
    for emo, c in counts.items():
        print(f"{emo}: {c/total*100:.2f}%")

    sad_pct = (counts.get("sad", 0) / total) * 100
    fear_pct = (counts.get("fear", 0) / total) * 100
    angry_pct = (counts.get("angry", 0) / total) * 100

    print("\n=== Informe de comportamiento ===")
    if sad_pct > 35:
        print("⚠️ Tristeza elevada - posible estado depresivo")
    if fear_pct > 25:
        print("⚠️ Miedo/ansiedad elevada")
    if angry_pct > 30:
        print("⚠️ Irritabilidad elevada")
    if sad_pct < 35 and fear_pct < 25 and angry_pct < 30:
        print("🙂 Estado emocional estable")