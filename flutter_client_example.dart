// ============================================================
// CÓDIGO FLUTTER PARA ANÁLISIS EMOCIONAL EN TIEMPO REAL
// CON AUTENTICACIÓN JWT
// ============================================================
// 
// Dependencias necesarias en pubspec.yaml:
// 
// dependencies:
//   flutter:
//     sdk: flutter
//   web_socket_channel: ^3.0.0
//   camera: ^0.11.0
//   http: ^1.2.0
//   provider: ^6.1.0
//   flutter_secure_storage: ^9.0.0
//   jwt_decoder: ^2.0.1
// 
// ============================================================

// ---- 1. SERVICIO DE AUTENTICACIÓN ----
// lib/services/auth_service.dart

import 'dart:convert';
import 'dart:async';
import 'dart:typed_data';
import 'package:http/http.dart' as http;
// import 'package:flutter_secure_storage/flutter_secure_storage.dart';
// import 'package:jwt_decoder/jwt_decoder.dart';

class AuthService {
  static const String baseUrl = 'http://TU_IP_LOCAL:8000';
  
  // final FlutterSecureStorage _storage = FlutterSecureStorage();
  
  String? _accessToken;
  String? _refreshToken;
  
  String? get accessToken => _accessToken;
  bool get isAuthenticated => _accessToken != null;
  
  /// Headers con autenticación
  Map<String, String> get authHeaders => {
    'Content-Type': 'application/json',
    if (_accessToken != null) 'Authorization': 'Bearer $_accessToken',
  };
  
  /// Registrar nuevo usuario
  Future<AuthResult> register({
    required String username,
    required String email,
    required String password,
    required String firstName,
    required String lastName,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/api/auth/register/'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'username': username,
        'email': email,
        'password': password,
        'password_confirm': password,
        'first_name': firstName,
        'last_name': lastName,
      }),
    );
    
    if (response.statusCode == 201) {
      final data = jsonDecode(response.body);
      await _saveTokens(data['access'], data['refresh']);
      return AuthResult(
        success: true,
        user: User.fromJson(data['user']),
        message: 'Registro exitoso',
      );
    }
    
    return AuthResult(
      success: false,
      message: _extractError(response.body),
    );
  }
  
  /// Iniciar sesión
  Future<AuthResult> login({
    required String username,
    required String password,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/api/auth/login/'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'username': username,
        'password': password,
      }),
    );
    
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      await _saveTokens(data['access'], data['refresh']);
      return AuthResult(
        success: true,
        user: User.fromJson(data['user']),
        message: 'Login exitoso',
      );
    }
    
    return AuthResult(
      success: false,
      message: _extractError(response.body),
    );
  }
  
  /// Cerrar sesión
  Future<void> logout() async {
    if (_refreshToken != null) {
      await http.post(
        Uri.parse('$baseUrl/api/auth/logout/'),
        headers: authHeaders,
        body: jsonEncode({'refresh': _refreshToken}),
      );
    }
    await _clearTokens();
  }
  
  /// Refrescar token
  Future<bool> refreshTokens() async {
    if (_refreshToken == null) return false;
    
    final response = await http.post(
      Uri.parse('$baseUrl/api/auth/refresh/'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'refresh': _refreshToken}),
    );
    
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      _accessToken = data['access'];
      // await _storage.write(key: 'access_token', value: _accessToken);
      return true;
    }
    
    await _clearTokens();
    return false;
  }
  
  /// Obtener perfil del usuario
  Future<User?> getProfile() async {
    final response = await http.get(
      Uri.parse('$baseUrl/api/auth/profile/'),
      headers: authHeaders,
    );
    
    if (response.statusCode == 200) {
      return User.fromJson(jsonDecode(response.body));
    }
    return null;
  }
  
  /// Cambiar contraseña
  Future<bool> changePassword({
    required String oldPassword,
    required String newPassword,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/api/auth/change-password/'),
      headers: authHeaders,
      body: jsonEncode({
        'old_password': oldPassword,
        'new_password': newPassword,
        'new_password_confirm': newPassword,
      }),
    );
    
    return response.statusCode == 200;
  }
  
  /// Cargar tokens guardados
  Future<bool> loadSavedTokens() async {
    // _accessToken = await _storage.read(key: 'access_token');
    // _refreshToken = await _storage.read(key: 'refresh_token');
    
    if (_accessToken != null) {
      // Verificar si el token está expirado
      // if (JwtDecoder.isExpired(_accessToken!)) {
      //   return await refreshTokens();
      // }
      return true;
    }
    return false;
  }
  
  Future<void> _saveTokens(String access, String refresh) async {
    _accessToken = access;
    _refreshToken = refresh;
    // await _storage.write(key: 'access_token', value: access);
    // await _storage.write(key: 'refresh_token', value: refresh);
  }
  
  Future<void> _clearTokens() async {
    _accessToken = null;
    _refreshToken = null;
    // await _storage.deleteAll();
  }
  
  String _extractError(String body) {
    try {
      final data = jsonDecode(body);
      if (data is Map) {
        if (data.containsKey('detail')) return data['detail'];
        if (data.containsKey('error')) return data['error'];
        return data.values.first.toString();
      }
      return 'Error desconocido';
    } catch (e) {
      return 'Error de conexión';
    }
  }
}


class AuthResult {
  final bool success;
  final User? user;
  final String message;
  
  AuthResult({
    required this.success,
    this.user,
    required this.message,
  });
}


class User {
  final int id;
  final String username;
  final String email;
  final String firstName;
  final String lastName;
  
  User({
    required this.id,
    required this.username,
    required this.email,
    required this.firstName,
    required this.lastName,
  });
  
  factory User.fromJson(Map<String, dynamic> json) {
    return User(
      id: json['id'],
      username: json['username'],
      email: json['email'],
      firstName: json['first_name'] ?? '',
      lastName: json['last_name'] ?? '',
    );
  }
  
  String get fullName => '$firstName $lastName'.trim();
}

class EmotionService {
  static const String baseUrl = 'http://TU_IP_LOCAL:8000';
  static const String wsUrl = 'ws://TU_IP_LOCAL:8000';
  
  WebSocketChannel? _channel;
  StreamController<EmotionResult>? _resultController;
  
  Stream<EmotionResult> get resultStream => _resultController!.stream;
  
  /// Conectar al WebSocket para análisis en tiempo real
  Future<void> connect({int? personId}) async {
    _resultController = StreamController<EmotionResult>.broadcast();
    
    final url = personId != null 
        ? '$wsUrl/ws/analysis/$personId/'
        : '$wsUrl/ws/analysis/';
    
    _channel = WebSocketChannel.connect(Uri.parse(url));
    
    _channel!.stream.listen(
      (data) {
        final json = jsonDecode(data);
        
        if (json['type'] == 'analysis_result') {
          _resultController!.add(EmotionResult.fromJson(json));
        } else if (json['type'] == 'metrics') {
          // Manejar métricas si es necesario
        } else if (json['type'] == 'error') {
          _resultController!.addError(json['message']);
        }
      },
      onError: (error) {
        _resultController!.addError(error);
      },
      onDone: () {
        _resultController!.close();
      },
    );
  }
  
  /// Enviar frame de cámara para análisis
  void sendFrame(Uint8List imageBytes) {
    if (_channel == null) return;
    
    final base64Image = base64Encode(imageBytes);
    _channel!.sink.add(jsonEncode({
      'type': 'frame',
      'image': base64Image,
    }));
  }
  
  /// Solicitar métricas actuales
  void requestMetrics() {
    if (_channel == null) return;
    
    _channel!.sink.add(jsonEncode({
      'type': 'get_metrics',
    }));
  }
  
  /// Detener análisis
  void stop() {
    if (_channel == null) return;
    
    _channel!.sink.add(jsonEncode({
      'type': 'stop',
    }));
  }
  
  /// Desconectar
  void disconnect() {
    _channel?.sink.close();
    _resultController?.close();
  }
  
  // ---- API REST ----
  
  /// Obtener sesiones de una persona
  Future<List<Session>> getPersonSessions(int personId) async {
    final response = await http.get(
      Uri.parse('$baseUrl/api/persons/$personId/sessions/'),
    );
    
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      return (data['sessions'] as List)
          .map((s) => Session.fromJson(s))
          .toList();
    }
    throw Exception('Error al obtener sesiones');
  }
  
  /// Obtener detalle de una sesión
  Future<SessionDetail> getSessionDetail(int sessionId) async {
    final response = await http.get(
      Uri.parse('$baseUrl/api/sessions/$sessionId/'),
    );
    
    if (response.statusCode == 200) {
      return SessionDetail.fromJson(jsonDecode(response.body));
    }
    throw Exception('Error al obtener detalle de sesión');
  }
  
  /// Obtener reporte de comportamiento
  Future<BehaviorReport> getBehaviorReport(int personId) async {
    final response = await http.get(
      Uri.parse('$baseUrl/api/persons/$personId/report/'),
    );
    
    if (response.statusCode == 200) {
      return BehaviorReport.fromJson(jsonDecode(response.body));
    }
    throw Exception('Error al obtener reporte');
  }
  
  /// Obtener alertas de una persona
  Future<List<Alert>> getPersonAlerts(int personId) async {
    final response = await http.get(
      Uri.parse('$baseUrl/api/persons/$personId/alerts/'),
    );
    
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      return (data['alerts'] as List)
          .map((a) => Alert.fromJson(a))
          .toList();
    }
    throw Exception('Error al obtener alertas');
  }
}


// ---- 2. MODELOS ----
// lib/models/emotion_models.dart

class EmotionResult {
  final String? emotion;
  final Map<String, double> emotionScores;
  final bool headDown;
  final bool hunched;
  final bool handsOnFace;
  final String overallState;
  final String timestamp;
  
  EmotionResult({
    this.emotion,
    required this.emotionScores,
    required this.headDown,
    required this.hunched,
    required this.handsOnFace,
    required this.overallState,
    required this.timestamp,
  });
  
  factory EmotionResult.fromJson(Map<String, dynamic> json) {
    return EmotionResult(
      emotion: json['emotion'],
      emotionScores: Map<String, double>.from(json['emotion_scores'] ?? {}),
      headDown: json['head_down'] ?? false,
      hunched: json['hunched'] ?? false,
      handsOnFace: json['hands_on_face'] ?? false,
      overallState: json['overall_state'] ?? 'normal',
      timestamp: json['timestamp'] ?? '',
    );
  }
  
  String get stateEmoji {
    switch (overallState) {
      case 'anxious': return '😰';
      case 'stressed': return '😓';
      case 'nervous': return '😬';
      default: return '😊';
    }
  }
  
  String get emotionEmoji {
    switch (emotion) {
      case 'happy': return '😊';
      case 'sad': return '😢';
      case 'angry': return '😠';
      case 'fear': return '😨';
      case 'surprise': return '😲';
      case 'disgust': return '🤢';
      default: return '😐';
    }
  }
}


class Session {
  final int id;
  final String startedAt;
  final String? endedAt;
  final double? durationSeconds;
  final String overallState;
  final Map<String, double> emotionSummary;
  
  Session({
    required this.id,
    required this.startedAt,
    this.endedAt,
    this.durationSeconds,
    required this.overallState,
    required this.emotionSummary,
  });
  
  factory Session.fromJson(Map<String, dynamic> json) {
    return Session(
      id: json['id'],
      startedAt: json['started_at'],
      endedAt: json['ended_at'],
      durationSeconds: json['duration_seconds']?.toDouble(),
      overallState: json['overall_state'] ?? 'stable',
      emotionSummary: Map<String, double>.from(json['emotion_summary'] ?? {}),
    );
  }
}


class SessionDetail {
  final Session session;
  final Map<String, double> emotionSummary;
  final Map<String, int> postureSummary;
  final List<Alert> alerts;
  
  SessionDetail({
    required this.session,
    required this.emotionSummary,
    required this.postureSummary,
    required this.alerts,
  });
  
  factory SessionDetail.fromJson(Map<String, dynamic> json) {
    return SessionDetail(
      session: Session.fromJson(json['session']),
      emotionSummary: Map<String, double>.from(json['emotion_summary'] ?? {}),
      postureSummary: Map<String, int>.from(json['posture_summary'] ?? {}),
      alerts: (json['alerts'] as List? ?? [])
          .map((a) => Alert.fromJson(a))
          .toList(),
    );
  }
}


class Alert {
  final int? id;
  final String type;
  final String severity;
  final String message;
  final String createdAt;
  final bool isReviewed;
  
  Alert({
    this.id,
    required this.type,
    required this.severity,
    required this.message,
    required this.createdAt,
    this.isReviewed = false,
  });
  
  factory Alert.fromJson(Map<String, dynamic> json) {
    return Alert(
      id: json['id'],
      type: json['type'],
      severity: json['severity'],
      message: json['message'],
      createdAt: json['created_at'],
      isReviewed: json['is_reviewed'] ?? false,
    );
  }
  
  Color get severityColor {
    switch (severity) {
      case 'high': return Color(0xFFE53935);
      case 'medium': return Color(0xFFFF9800);
      default: return Color(0xFF4CAF50);
    }
  }
}


class BehaviorReport {
  final int totalSessions;
  final Map<String, double> averageEmotions;
  final Map<String, int> stateDistribution;
  final String overallTendency;
  final Recommendation recommendation;
  
  BehaviorReport({
    required this.totalSessions,
    required this.averageEmotions,
    required this.stateDistribution,
    required this.overallTendency,
    required this.recommendation,
  });
  
  factory BehaviorReport.fromJson(Map<String, dynamic> json) {
    return BehaviorReport(
      totalSessions: json['summary']['total_sessions'],
      averageEmotions: Map<String, double>.from(json['summary']['average_emotions'] ?? {}),
      stateDistribution: Map<String, int>.from(json['summary']['state_distribution'] ?? {}),
      overallTendency: json['summary']['overall_tendency'],
      recommendation: Recommendation.fromJson(json['recommendation']),
    );
  }
}


class Recommendation {
  final String level;
  final String message;
  final List<String> suggestions;
  
  Recommendation({
    required this.level,
    required this.message,
    required this.suggestions,
  });
  
  factory Recommendation.fromJson(Map<String, dynamic> json) {
    return Recommendation(
      level: json['level'],
      message: json['message'],
      suggestions: List<String>.from(json['suggestions'] ?? []),
    );
  }
}


// ---- 3. WIDGET DE ANÁLISIS EN TIEMPO REAL ----
// lib/screens/analysis_screen.dart

/*
import 'package:flutter/material.dart';
import 'package:camera/camera.dart';

class AnalysisScreen extends StatefulWidget {
  final int personId;
  
  const AnalysisScreen({Key? key, required this.personId}) : super(key: key);
  
  @override
  _AnalysisScreenState createState() => _AnalysisScreenState();
}

class _AnalysisScreenState extends State<AnalysisScreen> {
  final EmotionService _service = EmotionService();
  CameraController? _cameraController;
  EmotionResult? _lastResult;
  bool _isAnalyzing = false;
  
  @override
  void initState() {
    super.initState();
    _initCamera();
    _connectWebSocket();
  }
  
  Future<void> _initCamera() async {
    final cameras = await availableCameras();
    final frontCamera = cameras.firstWhere(
      (camera) => camera.lensDirection == CameraLensDirection.front,
      orElse: () => cameras.first,
    );
    
    _cameraController = CameraController(
      frontCamera,
      ResolutionPreset.medium,
      enableAudio: false,
    );
    
    await _cameraController!.initialize();
    setState(() {});
  }
  
  Future<void> _connectWebSocket() async {
    await _service.connect(personId: widget.personId);
    
    _service.resultStream.listen((result) {
      setState(() {
        _lastResult = result;
      });
    });
  }
  
  void _startAnalysis() {
    if (_cameraController == null) return;
    
    setState(() => _isAnalyzing = true);
    
    // Capturar y enviar frames cada 500ms
    Timer.periodic(Duration(milliseconds: 500), (timer) async {
      if (!_isAnalyzing) {
        timer.cancel();
        return;
      }
      
      try {
        final image = await _cameraController!.takePicture();
        final bytes = await image.readAsBytes();
        _service.sendFrame(bytes);
      } catch (e) {
        print('Error capturando frame: $e');
      }
    });
  }
  
  void _stopAnalysis() {
    setState(() => _isAnalyzing = false);
    _service.stop();
  }
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Análisis Emocional'),
        actions: [
          IconButton(
            icon: Icon(Icons.analytics),
            onPressed: () => _service.requestMetrics(),
          ),
        ],
      ),
      body: Column(
        children: [
          // Vista de cámara
          Expanded(
            flex: 2,
            child: _cameraController?.value.isInitialized ?? false
                ? CameraPreview(_cameraController!)
                : Center(child: CircularProgressIndicator()),
          ),
          
          // Panel de resultados
          Expanded(
            child: Container(
              padding: EdgeInsets.all(16),
              color: Colors.grey[100],
              child: _lastResult != null
                  ? _buildResultPanel(_lastResult!)
                  : Center(child: Text('Presiona iniciar para analizar')),
            ),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _isAnalyzing ? _stopAnalysis : _startAnalysis,
        icon: Icon(_isAnalyzing ? Icons.stop : Icons.play_arrow),
        label: Text(_isAnalyzing ? 'Detener' : 'Iniciar'),
        backgroundColor: _isAnalyzing ? Colors.red : Colors.green,
      ),
    );
  }
  
  Widget _buildResultPanel(EmotionResult result) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Text(result.emotionEmoji, style: TextStyle(fontSize: 48)),
            SizedBox(width: 16),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Emoción: ${result.emotion ?? "Desconocida"}',
                  style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                ),
                Text('Estado: ${result.overallState}'),
              ],
            ),
          ],
        ),
        SizedBox(height: 16),
        if (result.headDown)
          _buildAlert('Cabeza baja detectada', Icons.arrow_downward),
        if (result.hunched)
          _buildAlert('Hombros encogidos', Icons.accessibility),
        if (result.handsOnFace)
          _buildAlert('Manos en la cara', Icons.pan_tool),
      ],
    );
  }
  
  Widget _buildAlert(String text, IconData icon) {
    return Container(
      padding: EdgeInsets.all(8),
      margin: EdgeInsets.only(bottom: 4),
      decoration: BoxDecoration(
        color: Colors.orange[100],
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        children: [
          Icon(icon, color: Colors.orange),
          SizedBox(width: 8),
          Text(text),
        ],
      ),
    );
  }
  
  @override
  void dispose() {
    _service.disconnect();
    _cameraController?.dispose();
    super.dispose();
  }
}
*/


// ---- 4. EJEMPLO DE USO ----
// 
// void main() async {
//   WidgetsFlutterBinding.ensureInitialized();
//   runApp(MyApp());
// }
// 
// class MyApp extends StatelessWidget {
//   @override
//   Widget build(BuildContext context) {
//     return MaterialApp(
//       title: 'Baymax Infantil',
//       home: AnalysisScreen(personId: 1),
//     );
//   }
// }
