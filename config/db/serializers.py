from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Person, AnalysisSession, EmotionRecord, PostureRecord, BehaviorAlert


# ============================================================
# SERIALIZERS DE AUTENTICACIÓN
# ============================================================

class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer para registro de usuarios"""
    password = serializers.CharField(
        write_only=True, 
        required=True, 
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        write_only=True, 
        required=True,
        style={'input_type': 'password'}
    )
    
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password', 'password_confirm', 'first_name', 'last_name')
        extra_kwargs = {
            'email': {'required': True},
            'first_name': {'required': True},
            'last_name': {'required': True},
        }
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({
                'password_confirm': 'Las contraseñas no coinciden.'
            })
        
        if User.objects.filter(email=attrs['email']).exists():
            raise serializers.ValidationError({
                'email': 'Este email ya está registrado.'
            })
        
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', '')
        )
        return user


class UserLoginSerializer(serializers.Serializer):
    """Serializer para login de usuarios"""
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True, write_only=True, style={'input_type': 'password'})
    
    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')
        
        user = authenticate(username=username, password=password)
        
        if not user:
            raise serializers.ValidationError({
                'detail': 'Credenciales inválidas.'
            })
        
        if not user.is_active:
            raise serializers.ValidationError({
                'detail': 'Usuario desactivado.'
            })
        
        attrs['user'] = user
        return attrs


class UserSerializer(serializers.ModelSerializer):
    """Serializer para información del usuario"""
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'date_joined', 'is_active')
        read_only_fields = ('id', 'date_joined', 'is_active')


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer para cambio de contraseña"""
    old_password = serializers.CharField(required=True, write_only=True, style={'input_type': 'password'})
    new_password = serializers.CharField(required=True, write_only=True, validators=[validate_password], style={'input_type': 'password'})
    new_password_confirm = serializers.CharField(required=True, write_only=True, style={'input_type': 'password'})
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({
                'new_password_confirm': 'Las contraseñas no coinciden.'
            })
        return attrs


class TokenResponseSerializer(serializers.Serializer):
    """Serializer para respuesta de tokens"""
    access = serializers.CharField()
    refresh = serializers.CharField()
    user = UserSerializer()


# ============================================================
# SERIALIZERS DE PERSONAS
# ============================================================

class PersonSerializer(serializers.ModelSerializer):
    """Serializer completo para Person"""
    age = serializers.SerializerMethodField()
    sessions_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Person
        fields = '__all__'
        extra_kwargs = {
            'password': {'write_only': True}
        }
    
    def get_age(self, obj):
        if obj.birthdate:
            from datetime import date
            today = date.today()
            return today.year - obj.birthdate.year - (
                (today.month, today.day) < (obj.birthdate.month, obj.birthdate.day)
            )
        return None
    
    def get_sessions_count(self, obj):
        return obj.sessions.count()


class PersonCreateSerializer(serializers.ModelSerializer):
    """Serializer para crear Person"""
    class Meta:
        model = Person
        fields = ('first_name', 'last_name', 'email', 'password', 'birthdate', 'genere')
        extra_kwargs = {
            'password': {'write_only': True}
        }


class PersonListSerializer(serializers.ModelSerializer):
    """Serializer simplificado para listar Persons"""
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Person
        fields = ('id', 'full_name', 'email', 'date_joined')
    
    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"


# ============================================================
# SERIALIZERS DE EMOCIONES Y POSTURAS
# ============================================================

class EmotionRecordSerializer(serializers.ModelSerializer):
    """Serializer para EmotionRecord"""
    emotion_display = serializers.CharField(source='get_dominant_emotion_display', read_only=True)
    
    class Meta:
        model = EmotionRecord
        fields = '__all__'


class EmotionScoresSerializer(serializers.Serializer):
    """Serializer para scores de emociones"""
    happy = serializers.FloatField()
    sad = serializers.FloatField()
    angry = serializers.FloatField()
    fear = serializers.FloatField()
    surprise = serializers.FloatField()
    disgust = serializers.FloatField()
    neutral = serializers.FloatField()


class PostureRecordSerializer(serializers.ModelSerializer):
    """Serializer para PostureRecord"""
    posture_description = serializers.SerializerMethodField()
    
    class Meta:
        model = PostureRecord
        fields = '__all__'
    
    def get_posture_description(self, obj):
        flags = []
        if obj.head_down:
            flags.append("Cabeza baja")
        if obj.hunched_shoulders:
            flags.append("Hombros encogidos")
        if obj.hands_on_face:
            flags.append("Manos en cara")
        return ', '.join(flags) if flags else 'Normal'


# ============================================================
# SERIALIZERS DE SESIONES
# ============================================================

class AnalysisSessionSerializer(serializers.ModelSerializer):
    """Serializer completo para AnalysisSession"""
    person_name = serializers.SerializerMethodField()
    emotion_summary = serializers.SerializerMethodField()
    posture_summary = serializers.SerializerMethodField()
    overall_state_display = serializers.CharField(source='get_overall_state_display', read_only=True)
    
    class Meta:
        model = AnalysisSession
        fields = '__all__'
    
    def get_person_name(self, obj):
        return f"{obj.person.first_name} {obj.person.last_name}"
    
    def get_emotion_summary(self, obj):
        return {
            'happy': obj.happy_pct,
            'sad': obj.sad_pct,
            'angry': obj.angry_pct,
            'fear': obj.fear_pct,
            'surprise': obj.surprise_pct,
            'disgust': obj.disgust_pct,
            'neutral': obj.neutral_pct,
        }
    
    def get_posture_summary(self, obj):
        return {
            'head_down_count': obj.head_down_count,
            'hunched_count': obj.hunched_count,
            'hands_on_face_count': obj.hands_on_face_count,
        }


class AnalysisSessionListSerializer(serializers.ModelSerializer):
    """Serializer simplificado para listar sesiones"""
    person_name = serializers.SerializerMethodField()
    duration = serializers.SerializerMethodField()
    
    class Meta:
        model = AnalysisSession
        fields = ('id', 'person_name', 'started_at', 'ended_at', 'duration', 'overall_state')
    
    def get_person_name(self, obj):
        return f"{obj.person.first_name} {obj.person.last_name}"
    
    def get_duration(self, obj):
        if obj.duration_seconds:
            minutes = int(obj.duration_seconds // 60)
            seconds = int(obj.duration_seconds % 60)
            return f"{minutes}m {seconds}s"
        return None


class AnalysisSessionDetailSerializer(serializers.ModelSerializer):
    """Serializer detallado con emociones y posturas"""
    person = PersonListSerializer(read_only=True)
    emotions = EmotionRecordSerializer(many=True, read_only=True)
    postures = PostureRecordSerializer(many=True, read_only=True)
    alerts = serializers.SerializerMethodField()
    emotion_summary = serializers.SerializerMethodField()
    posture_summary = serializers.SerializerMethodField()
    
    class Meta:
        model = AnalysisSession
        fields = '__all__'
    
    def get_alerts(self, obj):
        return BehaviorAlertSerializer(obj.alerts.all(), many=True).data
    
    def get_emotion_summary(self, obj):
        return {
            'happy': obj.happy_pct,
            'sad': obj.sad_pct,
            'angry': obj.angry_pct,
            'fear': obj.fear_pct,
            'surprise': obj.surprise_pct,
            'disgust': obj.disgust_pct,
            'neutral': obj.neutral_pct,
        }
    
    def get_posture_summary(self, obj):
        return {
            'head_down_count': obj.head_down_count,
            'hunched_count': obj.hunched_count,
            'hands_on_face_count': obj.hands_on_face_count,
        }


# ============================================================
# SERIALIZERS DE ALERTAS
# ============================================================

class BehaviorAlertSerializer(serializers.ModelSerializer):
    """Serializer para BehaviorAlert"""
    alert_type_display = serializers.CharField(source='get_alert_type_display', read_only=True)
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)
    session_info = serializers.SerializerMethodField()
    
    class Meta:
        model = BehaviorAlert
        fields = '__all__'
    
    def get_session_info(self, obj):
        return {
            'id': obj.session.id,
            'started_at': obj.session.started_at,
            'person_name': f"{obj.session.person.first_name} {obj.session.person.last_name}"
        }


class BehaviorAlertListSerializer(serializers.ModelSerializer):
    """Serializer simplificado para listar alertas"""
    class Meta:
        model = BehaviorAlert
        fields = ('id', 'alert_type', 'severity', 'message', 'created_at', 'is_reviewed')


# ============================================================
# SERIALIZERS DE REPORTES
# ============================================================

class RecommendationSerializer(serializers.Serializer):
    """Serializer para recomendaciones"""
    level = serializers.CharField()
    message = serializers.CharField()
    suggestions = serializers.ListField(child=serializers.CharField())


class BehaviorReportSerializer(serializers.Serializer):
    """Serializer para reporte de comportamiento"""
    person = PersonListSerializer()
    total_sessions = serializers.IntegerField()
    average_emotions = EmotionScoresSerializer()
    state_distribution = serializers.DictField()
    alert_summary = serializers.DictField()
    overall_tendency = serializers.CharField()
    recommendation = RecommendationSerializer()


# ============================================================
# SERIALIZERS PARA WEBSOCKET
# ============================================================

class WebSocketFrameSerializer(serializers.Serializer):
    """Serializer para frames enviados por WebSocket"""
    type = serializers.CharField()
    image = serializers.CharField(required=False)  # Base64 encoded


class WebSocketResultSerializer(serializers.Serializer):
    """Serializer para resultados de análisis en tiempo real"""
    type = serializers.CharField()
    emotion = serializers.CharField(allow_null=True)
    emotion_scores = serializers.DictField()
    head_down = serializers.BooleanField()
    hunched = serializers.BooleanField()
    hands_on_face = serializers.BooleanField()
    overall_state = serializers.CharField()
    timestamp = serializers.DateTimeField()
