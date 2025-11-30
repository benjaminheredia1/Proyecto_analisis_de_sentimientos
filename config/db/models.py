from django.db import models
from django.utils import timezone

class Person(models.Model):
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=100)
    date_joined = models.DateTimeField(default=timezone.now)
    birthdate = models.DateField(null=True, blank=True)
    genere = models.CharField(max_length=10, null=False, blank=True)
    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class AnalysisSession(models.Model):
    """Sesión de análisis emocional"""
    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name='sessions')
    started_at = models.DateTimeField(default=timezone.now)
    ended_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.FloatField(null=True, blank=True)
    
    # Resumen de emociones (porcentajes)
    happy_pct = models.FloatField(default=0)
    sad_pct = models.FloatField(default=0)
    angry_pct = models.FloatField(default=0)
    fear_pct = models.FloatField(default=0)
    surprise_pct = models.FloatField(default=0)
    disgust_pct = models.FloatField(default=0)
    neutral_pct = models.FloatField(default=0)
    
    # Resumen de posturas
    head_down_count = models.IntegerField(default=0)
    hunched_count = models.IntegerField(default=0)
    hands_on_face_count = models.IntegerField(default=0)
    
    # Estado general calculado
    ESTADO_CHOICES = [
        ('stable', 'Estable'),
        ('anxious', 'Ansiedad detectada'),
        ('sad', 'Tristeza detectada'),
        ('stressed', 'Estrés detectado'),
        ('nervous', 'Nerviosismo detectado'),
    ]
    overall_state = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='stable')
    notes = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"Sesión {self.id} - {self.person} - {self.started_at.strftime('%Y-%m-%d %H:%M')}"
    
    class Meta:
        ordering = ['-started_at']


class EmotionRecord(models.Model):
    """Registro individual de emoción detectada"""
    session = models.ForeignKey(AnalysisSession, on_delete=models.CASCADE, related_name='emotions')
    timestamp = models.DateTimeField(default=timezone.now)
    
    # Emoción dominante
    EMOTION_CHOICES = [
        ('happy', 'Feliz'),
        ('sad', 'Triste'),
        ('angry', 'Enojado'),
        ('fear', 'Miedo'),
        ('surprise', 'Sorpresa'),
        ('disgust', 'Disgusto'),
        ('neutral', 'Neutral'),
    ]
    dominant_emotion = models.CharField(max_length=15, choices=EMOTION_CHOICES)
    
    # Scores de cada emoción (0-100)
    happy_score = models.FloatField(default=0)
    sad_score = models.FloatField(default=0)
    angry_score = models.FloatField(default=0)
    fear_score = models.FloatField(default=0)
    surprise_score = models.FloatField(default=0)
    disgust_score = models.FloatField(default=0)
    neutral_score = models.FloatField(default=0)
    
    def __str__(self):
        return f"{self.dominant_emotion} - {self.timestamp.strftime('%H:%M:%S')}"
    
    class Meta:
        ordering = ['timestamp']


class PostureRecord(models.Model):
    """Registro individual de postura detectada"""
    session = models.ForeignKey(AnalysisSession, on_delete=models.CASCADE, related_name='postures')
    timestamp = models.DateTimeField(default=timezone.now)
    
    # Indicadores de postura
    head_down = models.BooleanField(default=False)
    hunched_shoulders = models.BooleanField(default=False)
    hands_on_face = models.BooleanField(default=False)
    
    # Keypoints detectados (coordenadas normalizadas)
    nose_x = models.FloatField(null=True, blank=True)
    nose_y = models.FloatField(null=True, blank=True)
    left_shoulder_x = models.FloatField(null=True, blank=True)
    left_shoulder_y = models.FloatField(null=True, blank=True)
    right_shoulder_x = models.FloatField(null=True, blank=True)
    right_shoulder_y = models.FloatField(null=True, blank=True)
    
    def __str__(self):
        flags = []
        if self.head_down:
            flags.append("Cabeza baja")
        if self.hunched_shoulders:
            flags.append("Hombros encogidos")
        if self.hands_on_face:
            flags.append("Manos en cara")
        return f"{', '.join(flags) or 'Normal'} - {self.timestamp.strftime('%H:%M:%S')}"
    
    class Meta:
        ordering = ['timestamp']


class BehaviorAlert(models.Model):
    """Alertas de comportamiento generadas automáticamente"""
    session = models.ForeignKey(AnalysisSession, on_delete=models.CASCADE, related_name='alerts')
    created_at = models.DateTimeField(default=timezone.now)
    
    ALERT_TYPE_CHOICES = [
        ('high_sadness', 'Tristeza elevada'),
        ('high_anxiety', 'Ansiedad elevada'),
        ('high_anger', 'Irritabilidad elevada'),
        ('nervous_behavior', 'Comportamiento nervioso'),
        ('depressive_posture', 'Postura depresiva'),
    ]
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPE_CHOICES)
    
    SEVERITY_CHOICES = [
        ('low', 'Baja'),
        ('medium', 'Media'),
        ('high', 'Alta'),
    ]
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default='low')
    
    message = models.TextField()
    is_reviewed = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.get_alert_type_display()} ({self.severity}) - {self.session.person}"
    
    class Meta:
        ordering = ['-created_at']
