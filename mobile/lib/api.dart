import 'dart:convert';
import 'dart:math';

import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

const apiBase = String.fromEnvironment(
  'API_BASE_URL',
  defaultValue: 'https://techwatch.zivantaai.com',
);

class TechWatchApi {
  TechWatchApi(this.storage, this.installationId);

  final SharedPreferences storage;
  String installationId;

  static Future<TechWatchApi> open() async {
    final storage = await SharedPreferences.getInstance();
    var id = storage.getString('installation_id');
    if (id == null) {
      id = _newId();
      await storage.setString('installation_id', id);
    }
    return TechWatchApi(storage, id);
  }

  static String _newId() {
    final random = Random.secure();
    return List.generate(
      24,
      (_) => random.nextInt(256).toRadixString(16).padLeft(2, '0'),
    ).join();
  }

  Future<dynamic> request(
    String path, {
    String method = 'GET',
    Object? body,
  }) async {
    final uri = Uri.parse('$apiBase$path');
    final headers = <String, String>{'X-Installation-ID': installationId};
    if (body != null) headers['Content-Type'] = 'application/json';
    final response = await switch (method) {
      'PUT' =>
        http
            .put(uri, headers: headers, body: jsonEncode(body))
            .timeout(const Duration(seconds: 12)),
      'DELETE' =>
        http.delete(uri, headers: headers).timeout(const Duration(seconds: 12)),
      _ => http.get(uri, headers: headers).timeout(const Duration(seconds: 12)),
    };
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw Exception('Server returned ${response.statusCode}');
    }
    return jsonDecode(utf8.decode(response.bodyBytes));
  }

  Future<Map<String, dynamic>> getMap(String path) async =>
      Map<String, dynamic>.from(await request(path) as Map);

  Future<Map<String, dynamic>> cachedMap(String path, String key) async {
    try {
      final result = await getMap(path);
      await storage.setString(key, jsonEncode(result));
      return result;
    } catch (_) {
      final cached = storage.getString(key);
      if (cached != null) {
        return Map<String, dynamic>.from(jsonDecode(cached) as Map);
      }
      rethrow;
    }
  }

  Future<void> deleteMyData() async {
    await request('/v1/me', method: 'DELETE');
    installationId = _newId();
    await storage.clear();
    await storage.setString('installation_id', installationId);
  }
}

List<String> strings(dynamic value) =>
    (value is List ? value : const []).map((item) => item.toString()).toList();

List<Map<String, dynamic>> records(dynamic value) =>
    (value is List ? value : const [])
        .whereType<Map>()
        .map((item) => Map<String, dynamic>.from(item))
        .toList();
