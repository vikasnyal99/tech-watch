import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:share_plus/share_plus.dart';
import 'package:url_launcher/url_launcher.dart';

import 'api.dart';

const ink = Color(0xFF241813),
    muted = Color(0xFF6C6661),
    clay = Color(0xFFB74420);
const cream = Color(0xFFFCF9F4),
    line = Color(0xFFE7DED5),
    soft = Color(0xFFF7EFE7);

void main() => runApp(
  MaterialApp(
    title: 'TechWatch',
    debugShowCheckedModeBanner: false,
    theme: ThemeData(
      useMaterial3: true,
      scaffoldBackgroundColor: cream,
      colorScheme: ColorScheme.fromSeed(seedColor: clay, surface: cream),
      appBarTheme: const AppBarTheme(
        backgroundColor: cream,
        foregroundColor: ink,
      ),
      textTheme: const TextTheme(
        headlineLarge: TextStyle(
          fontFamily: 'serif',
          fontSize: 33,
          height: 1.06,
          color: ink,
        ),
        headlineMedium: TextStyle(
          fontFamily: 'serif',
          fontSize: 27,
          height: 1.1,
          color: ink,
        ),
        bodyMedium: TextStyle(fontSize: 14, height: 1.35, color: ink),
      ),
    ),
    home: const Boot(),
  ),
);

class Boot extends StatefulWidget {
  const Boot({super.key});
  @override
  State<Boot> createState() => _BootState();
}

class _BootState extends State<Boot> {
  TechWatchApi? api;
  Map<String, dynamic> catalog = {}, prefs = {};
  String? error;
  @override
  void initState() {
    super.initState();
    load();
  }

  Future<void> load() async {
    try {
      final client = await TechWatchApi.open();
      final values = await Future.wait([
        client.cachedMap('/v1/catalog', 'catalog'),
        client.cachedMap('/v1/preferences', 'preferences'),
      ]);
      if (mounted) {
        setState(() {
          api = client;
          catalog = values[0];
          prefs = values[1];
          error = null;
        });
      }
    } catch (_) {
      if (mounted) {
        setState(
          () => error =
              'Could not reach TechWatch. Check your connection and retry.',
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    if (api != null) {
      return prefs['onboarded'] == true
          ? Home(
              api: api!,
              catalog: catalog,
              prefs: prefs,
              onReset: () => setState(() => prefs = {}),
            )
          : Onboarding(
              api: api!,
              catalog: catalog,
              initial: prefs,
              done: (value) => setState(() => prefs = value),
            );
    }
    return Scaffold(
      body: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Image.asset('assets/branding/techwatch-monogram.png', width: 80),
            const SizedBox(height: 20),
            if (error == null)
              const CircularProgressIndicator(color: clay)
            else ...[
              Padding(
                padding: const EdgeInsets.all(24),
                child: Text(error!, textAlign: TextAlign.center),
              ),
              TextButton(onPressed: load, child: const Text('Retry')),
            ],
          ],
        ),
      ),
    );
  }
}

class Brand extends StatelessWidget {
  const Brand({super.key, this.width = 165});
  final double width;
  @override
  Widget build(BuildContext context) => Image.asset(
    'assets/branding/techwatch-lockup.png',
    width: width,
    fit: BoxFit.contain,
    alignment: Alignment.centerLeft,
    semanticLabel: 'TechWatch',
  );
}

class ActionButton extends StatelessWidget {
  const ActionButton(
    this.label,
    this.action, {
    super.key,
    this.icon = Icons.arrow_forward,
  });
  final String label;
  final VoidCallback? action;
  final IconData icon;
  @override
  Widget build(BuildContext context) => SizedBox(
    width: double.infinity,
    height: 48,
    child: FilledButton(
      onPressed: action,
      style: FilledButton.styleFrom(
        backgroundColor: clay,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(11)),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text(
            label,
            style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 15),
          ),
          const SizedBox(width: 8),
          Icon(icon, size: 18),
        ],
      ),
    ),
  );
}

IconData iconFor(String label) {
  final s = label.toLowerCase();
  if (s.contains('security')) return Icons.shield_outlined;
  if (s.contains('ai') || s.contains('model') || s.contains('openai')) {
    return Icons.psychology_outlined;
  }
  if (s.contains('cloud') || s.contains('aws') || s.contains('azure')) {
    return Icons.cloud_outlined;
  }
  if (s.contains('kubernetes') || s.contains('docker')) {
    return Icons.view_in_ar_outlined;
  }
  if (s.contains('database') || s.contains('postgres')) {
    return Icons.storage_outlined;
  }
  if (s.contains('frontend') || s.contains('react')) return Icons.web_outlined;
  if (s.contains('observability') || s.contains('sre')) {
    return Icons.monitor_heart_outlined;
  }
  if (s.contains('engineer') || s.contains('backend') || s.contains('python')) {
    return Icons.code;
  }
  return Icons.layers_outlined;
}

Widget techMark(String label, {double size = 25}) {
  const brands = <String, String>{
    'python': 'python',
    'typescript': 'typescript',
    'php': 'php',
    'kubernetes': 'kubernetes',
    'aws': 'aws',
    'openai': 'openai',
    'anthropic': 'anthropic',
    'react': 'react',
    'node.js': 'nodedotjs',
    'postgresql': 'postgresql',
    'redis': 'redis',
    'grafana': 'grafana',
    'fastapi': 'fastapi',
    'vue': 'vuedotjs',
    'terraform': 'terraform',
    'laravel': 'laravel',
    'elasticsearch': 'elasticsearch',
    'linux': 'linux',
    'mysql': 'mysql',
    'mongodb': 'mongodb',
    'kafka': 'apachekafka',
  };
  final brand = brands[label.toLowerCase()];
  if (brand != null) {
    return Image.asset(
      'assets/brands/$brand.png',
      width: size,
      height: size,
      fit: BoxFit.contain,
      semanticLabel: label,
    );
  }
  return Icon(iconFor(label), color: clay, size: size);
}

class ChoiceTile extends StatelessWidget {
  const ChoiceTile({
    super.key,
    required this.label,
    required this.selected,
    required this.tap,
  });
  final String label;
  final bool selected;
  final VoidCallback tap;
  @override
  Widget build(BuildContext context) => InkWell(
    onTap: tap,
    borderRadius: BorderRadius.circular(12),
    child: Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: selected ? const Color(0xFFFFF7F1) : Colors.white,
        border: Border.all(
          color: selected ? clay : line,
          width: selected ? 1.5 : 1,
        ),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              techMark(label),
              Icon(
                selected ? Icons.check_circle : Icons.circle_outlined,
                color: selected ? clay : muted,
                size: 19,
              ),
            ],
          ),
          Text(
            label,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(fontSize: 13),
          ),
        ],
      ),
    ),
  );
}

class Onboarding extends StatefulWidget {
  const Onboarding({
    super.key,
    required this.api,
    required this.catalog,
    required this.initial,
    required this.done,
  });
  final TechWatchApi api;
  final Map<String, dynamic> catalog, initial;
  final ValueChanged<Map<String, dynamic>> done;
  @override
  State<Onboarding> createState() => _OnboardingState();
}

class _OnboardingState extends State<Onboarding> {
  int step = 0;
  String search = '';
  bool saving = false;
  late final roles = strings(widget.initial['roles']).toSet();
  late final topics = strings(widget.initial['topics']).toSet();
  late final follows = strings(widget.initial['follows']).toSet();
  late final signals = strings(widget.initial['signals']).toSet();
  void toggle(Set<String> set, String value) =>
      setState(() => set.contains(value) ? set.remove(value) : set.add(value));
  Future<void> finish() async {
    if (saving) return;
    setState(() => saving = true);
    final data = <String, dynamic>{
      ...widget.initial,
      'roles': roles.toList(),
      'topics': topics.toList(),
      'follows': follows.toList(),
      'signals': signals.toList(),
      'alert_delivery': 'in_app',
      'onboarded': true,
    };
    try {
      final value = Map<String, dynamic>.from(
        await widget.api.request('/v1/preferences', method: 'PUT', body: data)
            as Map,
      );
      await widget.api.storage.setString('preferences', jsonEncode(value));
      widget.done(value);
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Could not save setup. Try again.')),
        );
      }
    } finally {
      if (mounted) setState(() => saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final choices =
        strings(
              widget.catalog[step == 0
                  ? 'roles'
                  : step == 1
                  ? 'topics'
                  : 'technologies'],
            )
            .where((item) => item.toLowerCase().contains(search.toLowerCase()))
            .toList();
    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 15),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  if (step == 0)
                    const Brand(width: 146)
                  else
                    IconButton(
                      onPressed: () => setState(() {
                        step--;
                        search = '';
                      }),
                      icon: const Icon(Icons.arrow_back_ios_new, size: 19),
                    ),
                  const Spacer(),
                  ...List.generate(
                    4,
                    (i) => Container(
                      width: 20,
                      height: 5,
                      margin: const EdgeInsets.only(left: 4),
                      decoration: BoxDecoration(
                        color: i <= step ? clay : line,
                        borderRadius: BorderRadius.circular(9),
                      ),
                    ),
                  ),
                  const SizedBox(width: 9),
                  Text(
                    '${step + 1}/4',
                    style: const TextStyle(fontSize: 12, color: muted),
                  ),
                ],
              ),
              const SizedBox(height: 25),
              Text(
                [
                  'Stay ahead in tech.',
                  'What should we watch?',
                  'Follow your stack.',
                  'Choose your Alerts.',
                ][step],
                style: Theme.of(context).textTheme.headlineLarge,
              ),
              const SizedBox(height: 8),
              Text(
                [
                  'Software, AI, cloud and security updates—clearly explained for your work.',
                  'Choose the areas relevant to your work.',
                  'Select the technologies you use or evaluate.',
                  'Keep alerts useful and focused.',
                ][step],
                style: const TextStyle(color: muted, fontSize: 15, height: 1.3),
              ),
              const SizedBox(height: 18),
              if (step == 0) ...[
                Container(
                  height: 105,
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: soft,
                    borderRadius: BorderRadius.circular(14),
                  ),
                  child: Row(
                    children: [
                      const Expanded(
                        child: Text(
                          'Releases · Advisories\nBreaking changes · AI\nOne practical briefing at a time.',
                          style: TextStyle(height: 1.55, fontSize: 13),
                        ),
                      ),
                      ClipRRect(
                        borderRadius: BorderRadius.circular(8),
                        child: Image.asset(
                          'assets/images/onboarding-briefings.webp',
                          width: 86,
                          height: 83,
                          fit: BoxFit.cover,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 16),
                const Text(
                  'What best describes your work?',
                  style: TextStyle(fontFamily: 'serif', fontSize: 21),
                ),
                const Text(
                  'Choose more than one.',
                  style: TextStyle(color: muted),
                ),
                const SizedBox(height: 12),
              ],
              if (step == 1 || step == 2)
                Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: TextField(
                    onChanged: (value) => setState(() => search = value),
                    decoration: InputDecoration(
                      prefixIcon: const Icon(Icons.search),
                      hintText: step == 1
                          ? 'Search focus areas...'
                          : 'Search technologies...',
                      filled: true,
                      fillColor: Colors.white,
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
                    ),
                  ),
                ),
              Expanded(
                child: step == 3
                    ? alerts()
                    : GridView.builder(
                        itemCount: choices.length,
                        gridDelegate:
                            const SliverGridDelegateWithFixedCrossAxisCount(
                              crossAxisCount: 2,
                              crossAxisSpacing: 10,
                              mainAxisSpacing: 10,
                              childAspectRatio: 1.52,
                            ),
                        itemBuilder: (_, i) {
                          final item = choices[i];
                          final set = step == 0
                              ? roles
                              : step == 1
                              ? topics
                              : follows;
                          return ChoiceTile(
                            label: item,
                            selected: set.contains(item),
                            tap: () => toggle(set, item),
                          );
                        },
                      ),
              ),
              const SizedBox(height: 9),
              ActionButton(
                step == 3 ? 'Open my Feed' : 'Continue',
                saving
                    ? null
                    : () {
                        if (step < 3) {
                          setState(() {
                            step++;
                            search = '';
                          });
                        } else {
                          finish();
                        }
                      },
              ),
              if (step == 0)
                Center(
                  child: TextButton(
                    onPressed: finish,
                    child: const Text(
                      'Skip setup',
                      style: TextStyle(color: muted),
                    ),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }

  Widget alerts() => ListView(
    children: [
      for (final item in const [
        (
          'Security advisories',
          'Vulnerabilities, updates and mitigations.',
          Icons.shield_outlined,
        ),
        (
          'Breaking changes & deprecations',
          'Changes that may affect your work.',
          Icons.warning_amber_outlined,
        ),
        (
          'Major releases',
          'Stable releases from projects you follow.',
          Icons.inventory_2_outlined,
        ),
        (
          'AI model & API updates',
          'Models, APIs and developer tooling.',
          Icons.psychology_outlined,
        ),
      ])
        InkWell(
          onTap: () => toggle(signals, item.$1),
          child: Container(
            margin: const EdgeInsets.only(bottom: 9),
            padding: const EdgeInsets.all(13),
            decoration: BoxDecoration(
              color: Colors.white,
              border: Border.all(color: line),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Row(
              children: [
                Icon(item.$3, color: clay),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        item.$1,
                        style: const TextStyle(fontWeight: FontWeight.w600),
                      ),
                      Text(
                        item.$2,
                        style: const TextStyle(fontSize: 12, color: muted),
                      ),
                    ],
                  ),
                ),
                Icon(
                  signals.contains(item.$1)
                      ? Icons.check_box
                      : Icons.check_box_outline_blank,
                  color: clay,
                ),
              ],
            ),
          ),
        ),
      const SizedBox(height: 13),
      const Text(
        'How should we deliver alerts?',
        style: TextStyle(fontFamily: 'serif', fontSize: 21),
      ),
      const ListTile(
        leading: Icon(Icons.radio_button_checked, color: clay),
        title: Text('In-app only'),
        subtitle: Text('See updates in your TechWatch feed.'),
      ),
      const Padding(
        padding: EdgeInsets.all(10),
        child: Text(
          'Push alerts are not available in this preview.',
          style: TextStyle(color: muted, fontSize: 12),
        ),
      ),
    ],
  );
}

class Home extends StatefulWidget {
  const Home({
    super.key,
    required this.api,
    required this.catalog,
    required this.prefs,
    required this.onReset,
  });
  final TechWatchApi api;
  final Map<String, dynamic> catalog, prefs;
  final VoidCallback onReset;
  @override
  State<Home> createState() => _HomeState();
}

class _HomeState extends State<Home> {
  int destination = 0, section = 0, focus = 0;
  bool listMode = false, loading = true;
  String topic = '', query = '';
  String? error;
  List<Map<String, dynamic>> items = [], saved = [], searchResults = [];
  Map<String, dynamic>? health;
  String? healthError;
  final pagerKey = GlobalKey<EditorialPagerState>();
  final searchController = TextEditingController();
  static const sections = ['Feed', 'Your Stack', 'Trending', 'AI'];
  static const sectionIds = ['feed', 'stack', 'trending', 'ai'];
  @override
  void initState() {
    super.initState();
    refresh();
    loadSaved();
    loadHealth();
  }

  @override
  void dispose() {
    searchController.dispose();
    super.dispose();
  }

  Future<void> refresh() async {
    setState(() {
      loading = true;
      error = null;
    });
    try {
      final path =
          '/v1/feed?section=${sectionIds[section]}&topic=${Uri.encodeQueryComponent(topic)}';
      final data = await widget.api.cachedMap(
        path,
        'feed_${sectionIds[section]}_$topic',
      );
      if (mounted) {
        setState(() {
          items = records(data['items']);
          focus = 0;
          loading = false;
        });
        WidgetsBinding.instance.addPostFrameCallback((_) {
          if (mounted) pagerKey.currentState?.jumpToPage(0);
        });
      }
    } catch (_) {
      if (mounted) {
        setState(() {
          loading = false;
          error = 'Feed unavailable. Pull to retry.';
        });
      }
    }
  }

  Future<void> loadSaved() async {
    try {
      final data = await widget.api.getMap('/v1/bookmarks');
      if (mounted) setState(() => saved = records(data['items']));
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Could not load saved briefings.')),
        );
      }
    }
  }

  Future<void> loadHealth() async {
    try {
      final result = await widget.api.getMap('/v1/service-health');
      if (mounted) setState(() { health = result; healthError = null; });
    } catch (_) {
      if (mounted) setState(() => healthError = 'Service health is unavailable. Retry shortly.');
    }
  }

  Future<void> bookmark(Map<String, dynamic> item) async {
    final id = item['id'].toString(),
        wasSaved = saved.any((i) => i['id'] == id);
    try {
      await widget.api.request(
        '/v1/bookmarks/${Uri.encodeComponent(id)}',
        method: wasSaved ? 'DELETE' : 'PUT',
      );
      if (mounted) {
        setState(() {
          if (wasSaved) {
            saved.removeWhere((i) => i['id'] == id);
          } else {
            saved.add(item);
          }
        });
      }
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(wasSaved ? 'Removed from Saved' : 'Saved briefing'),
          ),
        );
      }
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Could not update Saved.')),
        );
      }
    }
  }

  Future<void> search(String value) async {
    setState(() => query = value);
    if (value.trim().isEmpty) {
      setState(() => searchResults = []);
      return;
    }
    try {
      final data = await widget.api.getMap(
        '/v1/search?q=${Uri.encodeQueryComponent(value.trim())}',
      );
      if (mounted && query == value) {
        setState(() => searchResults = records(data['stories']));
      }
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(const SnackBar(content: Text('Search unavailable.')));
      }
    }
  }

  Future<void> openSource(Map<String, dynamic> item) async {
    final raw = item['source_url']?.toString();
    if (raw == null || raw.isEmpty) return;
    final url = Uri.tryParse(raw);
    if (url == null || url.scheme != 'https') return;
    if (!await launchUrl(url, mode: LaunchMode.externalApplication) &&
        mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Could not open official source.')),
      );
    }
  }

  Future<void> shareBrief(Map<String, dynamic> item) async {
    final title = item['title']?.toString() ?? 'TechWatch briefing';
    final summary = item['summary']?.toString() ?? '';
    final source = item['source_url']?.toString();
    final label = item['fictional'] == true ? 'FICTIONAL SAMPLE: ' : '';
    final text = '$label$title\n$summary${source == null ? '' : '\n$source'}';
    await SharePlus.instance.share(ShareParams(text: text, subject: title));
  }

  void goSection(int value) {
    setState(() {
      section = value;
      topic = '';
    });
    refresh();
  }

  void goDestination(int value) {
    setState(() => destination = value);
    if (value == 2) loadHealth();
    if (value == 3) loadSaved();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    body: SafeArea(
      child: Column(
        children: [
          if (destination == 0) ...[
            header(),
            tabs(),
            controls(),
            Expanded(child: feedBody()),
          ] else if (destination == 1)
            Expanded(child: explore())
          else if (destination == 2)
            Expanded(child: healthScreen())
          else
            Expanded(child: savedScreen()),
        ],
      ),
    ),
    bottomNavigationBar: NavigationBar(
      height: 65,
      selectedIndex: destination,
      onDestinationSelected: goDestination,
      backgroundColor: cream,
      indicatorColor: soft,
      destinations: [
        NavigationDestination(
          icon: Icon(Icons.article_outlined),
          selectedIcon: Icon(Icons.article, color: clay),
          label: 'Briefs',
        ),
        NavigationDestination(
          icon: Icon(Icons.explore_outlined),
          selectedIcon: Icon(Icons.explore, color: clay),
          label: 'Explore',
        ),
        NavigationDestination(
          icon: Badge(
            isLabelVisible: (health?['active_count'] as int? ?? 0) > 0,
            label: Text('${health?['active_count'] ?? 0}'),
            child: const Icon(Icons.monitor_heart_outlined),
          ),
          selectedIcon: const Icon(Icons.monitor_heart, color: clay),
          label: 'Health',
        ),
        NavigationDestination(
          icon: Icon(Icons.bookmark_outline),
          selectedIcon: Icon(Icons.bookmark, color: clay),
          label: 'Saved',
        ),
      ],
    ),
  );
  Widget header() => Padding(
    padding: const EdgeInsets.fromLTRB(18, 5, 14, 1),
    child: Row(
      children: [
        const Brand(),
        const Spacer(),
        IconButton(
          tooltip: 'Search',
          onPressed: () => goDestination(1),
          icon: const Icon(Icons.search),
        ),
        IconButton(
          tooltip: 'Settings',
          onPressed: () => Navigator.of(context)
              .push(
                MaterialPageRoute(
                  builder: (_) => Settings(
                    api: widget.api,
                    prefs: widget.prefs,
                    catalog: widget.catalog,
                    onReset: widget.onReset,
                  ),
                ),
              )
              .then((_) => refresh()),
          icon: const Icon(Icons.account_circle_outlined),
        ),
      ],
    ),
  );
  Widget tabs() => Container(
    height: 47,
    decoration: const BoxDecoration(
      border: Border(bottom: BorderSide(color: line)),
    ),
    child: Row(
      children: List.generate(
        4,
        (i) => Expanded(
          child: InkWell(
            onTap: () => goSection(i),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                Text(
                  sections[i],
                  style: TextStyle(
                    color: section == i ? clay : muted,
                    fontWeight: section == i
                        ? FontWeight.w600
                        : FontWeight.w400,
                    fontSize: 13,
                  ),
                ),
                const SizedBox(height: 10),
                Container(
                  height: 2,
                  color: section == i ? clay : Colors.transparent,
                ),
              ],
            ),
          ),
        ),
      ),
    ),
  );
  Widget controls() => Padding(
    padding: const EdgeInsets.fromLTRB(12, 8, 12, 5),
    child: Row(
      children: [
        OutlinedButton.icon(
          onPressed: section == 1 ? editStack : filterTopics,
          icon: Icon(section == 1 ? Icons.layers_outlined : Icons.tune, size: 16),
          label: Text(
            section == 1 ? 'Your stack' : topic.isEmpty ? 'All updates' : topic,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
          style: OutlinedButton.styleFrom(
            foregroundColor: ink,
            side: const BorderSide(color: line),
            visualDensity: VisualDensity.compact,
          ),
        ),
        const Spacer(),
        if (!listMode && items.isNotEmpty)
          Text(
            '${focus + 1} of ${items.length} · Swipe up',
            style: const TextStyle(fontSize: 11, color: muted),
          ),
        const Spacer(),
        SegmentedButton<bool>(
          segments: const [
            ButtonSegment(value: false, icon: Icon(Icons.grid_view, size: 16)),
            ButtonSegment(value: true, icon: Icon(Icons.view_list, size: 17)),
          ],
          selected: {listMode},
          showSelectedIcon: false,
          style: ButtonStyle(
            visualDensity: VisualDensity.compact,
            padding: WidgetStateProperty.all(
              const EdgeInsets.symmetric(horizontal: 5),
            ),
          ),
          onSelectionChanged: (value) => setState(() => listMode = value.first),
        ),
      ],
    ),
  );
  Widget feedBody() {
    if (loading && items.isEmpty) {
      return const Center(child: CircularProgressIndicator(color: clay));
    }
    if (error != null && items.isEmpty) return empty(error!, refresh);
    if (items.isEmpty) {
      return empty(
        section == 1
            ? 'Follow technologies in onboarding to fill Your Stack.'
            : 'No reviewed briefings in this section yet.',
        refresh,
      );
    }
    if (listMode) {
      return RefreshIndicator(
        onRefresh: refresh,
        child: ListView.builder(
          itemCount: items.length,
          itemBuilder: (_, i) => storyRow(items[i], () {
            setState(() {
              focus = i;
              listMode = false;
            });
            WidgetsBinding.instance.addPostFrameCallback((_) {
              pagerKey.currentState?.jumpToPage(i);
            });
          }),
        ),
      );
    }
    return EditorialPager(
      key: pagerKey,
      items: items,
      initialIndex: focus,
      reducedMotion: widget.prefs['reduced_motion'] == true,
      onPageChanged: (i) => setState(() => focus = i),
      itemBuilder: (i) => Padding(
        padding: const EdgeInsets.fromLTRB(12, 0, 12, 8),
        child: BriefCard(
          item: items[i],
          saved: saved.any((s) => s['id'] == items[i]['id']),
          onSave: () => bookmark(items[i]),
          onShare: () => shareBrief(items[i]),
          onSource: () => openSource(items[i]),
        ),
      ),
    );
  }

  Widget empty(String message, VoidCallback action) => Center(
    child: Padding(
      padding: const EdgeInsets.all(30),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.article_outlined, size: 46, color: clay),
          const SizedBox(height: 15),
          Text(message, textAlign: TextAlign.center),
          const SizedBox(height: 15),
          TextButton(onPressed: action, child: const Text('Refresh')),
        ],
      ),
    ),
  );
  Future<void> filterTopics() async {
    final options = ['', ...strings(widget.catalog['topics'])];
    final selected = await showModalBottomSheet<String>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (context) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'Choose topics',
                style: TextStyle(fontFamily: 'serif', fontSize: 25),
              ),
              const Text(
                'Filter this section without changing your followed interests.',
                style: TextStyle(color: muted),
              ),
              const SizedBox(height: 15),
              SizedBox(
                height: MediaQuery.sizeOf(context).height * .48,
                child: ListView(
                  children: options
                      .map(
                        (item) => ListTile(
                          title: Text(item.isEmpty ? 'All updates' : item),
                          leading: Icon(
                            item.isEmpty ? Icons.grid_view : iconFor(item),
                            color: clay,
                          ),
                          trailing: topic == item
                              ? const Icon(Icons.check, color: clay)
                              : null,
                          onTap: () => Navigator.pop(context, item),
                        ),
                      )
                      .toList(),
                ),
              ),
            ],
          ),
        ),
      ),
    );
    if (selected != null && selected != topic) {
      setState(() => topic = selected);
      refresh();
    }
  }

  Future<void> editStack() async {
    final updated = await Navigator.push<bool>(
      context,
      MaterialPageRoute(
        builder: (_) => StackEditor(
          api: widget.api,
          prefs: widget.prefs,
          catalog: widget.catalog,
        ),
      ),
    );
    if (updated == true && mounted) refresh();
  }

  Widget storyRow(Map<String, dynamic> item, VoidCallback tap) => InkWell(
    onTap: tap,
    child: Container(
      padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 13),
      decoration: const BoxDecoration(
        border: Border(bottom: BorderSide(color: line)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 62,
            height: 62,
            decoration: BoxDecoration(
              color: soft,
              borderRadius: BorderRadius.circular(9),
            ),
            child: Center(
              child: techMark(item['technology']?.toString() ?? '', size: 34),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  item['technology']?.toString() ?? '',
                  style: const TextStyle(color: clay, fontSize: 12),
                ),
                Text(
                  item['title']?.toString() ?? '',
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    fontFamily: 'serif',
                    fontWeight: FontWeight.w600,
                    fontSize: 17,
                    height: 1.1,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  item['summary']?.toString() ?? '',
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontSize: 12, color: muted),
                ),
                if (item['fictional'] == true)
                  const Text(
                    'FICTIONAL SAMPLE',
                    style: TextStyle(color: clay, fontSize: 10),
                  ),
              ],
            ),
          ),
          IconButton(
            tooltip: 'Save',
            onPressed: () => bookmark(item),
            icon: Icon(
              saved.any((s) => s['id'] == item['id'])
                  ? Icons.bookmark
                  : Icons.bookmark_outline,
              size: 21,
            ),
          ),
        ],
      ),
    ),
  );
  Widget explore() => ListView(
    padding: const EdgeInsets.fromLTRB(18, 8, 18, 18),
    children: [
      Row(
        children: [
          const Brand(),
          const Spacer(),
          IconButton(
            onPressed: () => Navigator.push(
              context,
              MaterialPageRoute(
                builder: (_) => Settings(
                  api: widget.api,
                  prefs: widget.prefs,
                  catalog: widget.catalog,
                  onReset: widget.onReset,
                ),
              ),
            ).then((_) => refresh()),
            icon: const Icon(Icons.account_circle_outlined),
          ),
        ],
      ),
      const SizedBox(height: 20),
      const Text(
        'Follow your curiosity.',
        style: TextStyle(fontFamily: 'serif', fontSize: 28),
      ),
      const Text(
        'Explore topics, technologies and ideas shaping what is next in tech.',
        style: TextStyle(color: muted),
      ),
      const SizedBox(height: 17),
      TextField(
        controller: searchController,
        onChanged: search,
        decoration: InputDecoration(
          prefixIcon: const Icon(Icons.search),
          hintText: 'Search stories or technologies',
          filled: true,
          fillColor: Colors.white,
          border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
        ),
      ),
      const SizedBox(height: 14),
      if (query.isNotEmpty) ...[
        Text(
          '${searchResults.length} results',
          style: const TextStyle(color: muted),
        ),
        for (final item in searchResults)
          storyRow(
            item,
            () => showDialog<void>(
              context: context,
              builder: (_) => AlertDialog(
                title: Text(item['title']?.toString() ?? ''),
                content: Text(item['summary']?.toString() ?? ''),
                actions: [
                  TextButton(
                    onPressed: () => Navigator.pop(context),
                    child: const Text('Close'),
                  ),
                  if (item['source_url'] != null)
                    TextButton(
                      onPressed: () => openSource(item),
                      child: const Text('Read source'),
                    ),
                ],
              ),
            ),
          ),
      ] else ...[
        const Text(
          'Topics',
          style: TextStyle(fontFamily: 'serif', fontSize: 22),
        ),
        const SizedBox(height: 10),
        GridView.count(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          crossAxisCount: 2,
          childAspectRatio: 2.4,
          mainAxisSpacing: 8,
          crossAxisSpacing: 8,
          children: strings(widget.catalog['topics'])
              .map(
                (item) => InkWell(
                  onTap: () {
                    setState(() {
                      destination = 0;
                      section = 0;
                      topic = item;
                    });
                    refresh();
                  },
                  child: Container(
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      border: Border.all(color: line),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: Row(
                      children: [
                        Icon(iconFor(item), color: clay, size: 23),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            item,
                            maxLines: 2,
                            style: const TextStyle(fontSize: 12),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              )
              .toList(),
        ),
      ],
    ],
  );
  Widget healthScreen() {
    final incidents = records(health?['incidents']);
    final providers = records(health?['providers']);
    final offline = health?['offline'] == true;
    final complete = health?['complete'] == true;
    return RefreshIndicator(
      onRefresh: loadHealth,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(18, 20, 18, 90),
        children: [
          const Text('OFFICIAL SERVICE STATUS', style: TextStyle(color: clay, fontSize: 10, fontWeight: FontWeight.bold, letterSpacing: 2)),
          const SizedBox(height: 7),
          const Text('Service health', style: TextStyle(fontFamily: 'serif', fontSize: 32, color: ink)),
          const SizedBox(height: 7),
          const Text('Incidents reported by monitored providers. Check the official status page before acting.', style: TextStyle(color: muted, fontSize: 13)),
          const SizedBox(height: 17),
          if (healthError != null) Text(healthError!, style: const TextStyle(color: clay)),
          Card(
            color: incidents.isNotEmpty ? const Color(0xFFFFF2EB) : soft,
            child: ListTile(
              leading: const Icon(Icons.monitor_heart_outlined, color: clay),
              title: Text(offline ? 'Live status unavailable offline' : incidents.isNotEmpty ? '${incidents.length} active ${incidents.length == 1 ? 'issue' : 'issues'} reported' : complete ? 'No active issues reported' : 'Status coverage incomplete', style: const TextStyle(fontWeight: FontWeight.bold)),
              subtitle: const Text('From monitored official provider pages.'),
            ),
          ),
          if (health != null && !offline) ...[
            const SizedBox(height: 16),
            if (incidents.isNotEmpty) const Text('Active issues', style: TextStyle(fontFamily: 'serif', fontSize: 22)),
            ...incidents.map((incident) => Card(
              margin: const EdgeInsets.only(top: 9),
              child: Padding(
                padding: const EdgeInsets.all(13),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('${incident['provider']} · ${incident['status']}', style: const TextStyle(color: clay, fontSize: 12, fontWeight: FontWeight.bold)),
                  const SizedBox(height: 6),
                  Text('${incident['title']}', style: const TextStyle(fontFamily: 'serif', fontSize: 19)),
                  if ('${incident['summary'] ?? ''}'.isNotEmpty) ...[const SizedBox(height: 6), Text('${incident['summary']}', style: const TextStyle(fontSize: 13))],
                  TextButton(onPressed: () => openSource({'source_url': incident['url']}), child: const Text('View official status ↗')),
                ]),
              ),
            )),
            const SizedBox(height: 22),
            const Text('Monitored providers', style: TextStyle(fontFamily: 'serif', fontSize: 22)),
            ...providers.map((provider) => Card(
              margin: const EdgeInsets.only(top: 8),
              child: ListTile(
                title: Text('${provider['name']}'),
                subtitle: Text(provider['available'] == true ? '${provider['description']}' : 'Status temporarily unavailable'),
                trailing: Icon(provider['indicator'] == 'none' ? Icons.check_circle_outline : Icons.error_outline, color: provider['indicator'] == 'none' ? Colors.green.shade700 : clay),
                onTap: () => openSource({'source_url': provider['url']}),
              ),
            )),
            const SizedBox(height: 16),
            const Text('Public provider status may not reflect your account or region. This is separate from TechWatch source-fetch health.', style: TextStyle(fontSize: 11, color: muted)),
          ],
        ],
      ),
    );
  }

  Widget savedScreen() => Column(
    children: [
      Padding(
        padding: const EdgeInsets.fromLTRB(18, 13, 18, 12),
        child: Row(
          children: [
            const Text(
              'Saved briefings',
              style: TextStyle(fontFamily: 'serif', fontSize: 27),
            ),
            const Spacer(),
            IconButton(onPressed: loadSaved, icon: const Icon(Icons.refresh)),
          ],
        ),
      ),
      Expanded(
        child: saved.isEmpty
            ? empty('Save a briefing to read it here.', loadSaved)
            : ListView(
                children: saved
                    .map(
                      (item) => storyRow(
                        item,
                        () => showDialog<void>(
                          context: context,
                          builder: (_) => AlertDialog(
                            title: Text(item['title']?.toString() ?? ''),
                            content: Text(item['summary']?.toString() ?? ''),
                            actions: [
                              TextButton(
                                onPressed: () => Navigator.pop(context),
                                child: const Text('Close'),
                              ),
                              if (item['source_url'] != null)
                                TextButton(
                                  onPressed: () => openSource(item),
                                  child: const Text('Source'),
                                ),
                            ],
                          ),
                        ),
                      ),
                    )
                    .toList(),
              ),
      ),
    ],
  );
}

class EditorialPager extends StatefulWidget {
  const EditorialPager({
    super.key,
    required this.items,
    required this.initialIndex,
    required this.itemBuilder,
    required this.onPageChanged,
    required this.reducedMotion,
  });

  final List<Map<String, dynamic>> items;
  final int initialIndex;
  final Widget Function(int) itemBuilder;
  final ValueChanged<int> onPageChanged;
  final bool reducedMotion;

  @override
  State<EditorialPager> createState() => EditorialPagerState();
}

class EditorialPagerState extends State<EditorialPager>
    with SingleTickerProviderStateMixin {
  late final AnimationController motion;
  Animation<double> position = const AlwaysStoppedAnimation<double>(0);
  late int index;
  double progress = 0, viewportHeight = 1;
  bool settling = false;

  @override
  void initState() {
    super.initState();
    index = widget.initialIndex.clamp(0, widget.items.length - 1);
    motion = AnimationController(vsync: this);
    motion.addListener(() => setState(() => progress = position.value));
  }

  @override
  void didUpdateWidget(covariant EditorialPager oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (!identical(oldWidget.items, widget.items)) {
      motion.stop();
      settling = false;
      progress = 0;
      index = widget.initialIndex.clamp(0, widget.items.length - 1);
    }
  }

  @override
  void dispose() {
    motion.dispose();
    super.dispose();
  }

  void jumpToPage(int value) {
    if (widget.items.isEmpty) return;
    motion.stop();
    setState(() {
      index = value.clamp(0, widget.items.length - 1);
      progress = 0;
      settling = false;
    });
    widget.onPageChanged(index);
  }

  bool get reduced =>
      widget.reducedMotion || MediaQuery.disableAnimationsOf(context);

  Future<void> settle(bool commit) async {
    if (settling || widget.items.isEmpty) return;
    final direction = progress >= 0 ? 1 : -1;
    final next = index + direction;
    commit = commit && next >= 0 && next < widget.items.length;
    if (reduced) {
      if (commit) jumpToPage(next);
      return;
    }
    settling = true;
    final start = progress;
    motion.duration = Duration(milliseconds: commit ? 310 : 220);
    position =
        Tween<double>(
          begin: start,
          end: commit ? direction.toDouble() : 0,
        ).animate(
          CurvedAnimation(
            parent: motion,
            curve: commit ? Curves.easeOutCubic : Curves.easeOutBack,
          ),
        );
    try {
      await motion.forward(from: 0).orCancel;
    } catch (_) {
      return;
    }
    if (!mounted) return;
    setState(() {
      if (commit) index = next;
      progress = 0;
      settling = false;
    });
    if (commit) widget.onPageChanged(index);
  }

  void step(int direction) {
    if (settling ||
        index + direction < 0 ||
        index + direction >= widget.items.length) {
      return;
    }
    if (reduced) {
      jumpToPage(index + direction);
    } else {
      setState(() => progress = direction * .04);
      settle(true);
    }
  }

  @override
  Widget build(BuildContext context) => LayoutBuilder(
    builder: (context, size) {
      viewportHeight = size.maxHeight;
      final direction = progress >= 0 ? 1 : -1;
      final next = index + direction;
      final amount = progress.abs().clamp(0.0, 1.0);
      final showNext = amount > 0 && next >= 0 && next < widget.items.length;
      return Semantics(
        label: 'Briefing ${index + 1} of ${widget.items.length}',
        onIncrease: index < widget.items.length - 1 ? () => step(1) : null,
        onDecrease: index > 0 ? () => step(-1) : null,
        child: GestureDetector(
          behavior: HitTestBehavior.opaque,
          onVerticalDragStart: (_) {
            if (settling) return;
            motion.stop();
            setState(() => progress = 0);
          },
          onVerticalDragUpdate: (details) {
            if (settling) return;
            final nextProgress =
                (progress - details.primaryDelta! / viewportHeight).clamp(
                  -.88,
                  .88,
                );
            if (reduced) {
              progress = nextProgress;
            } else {
              setState(() => progress = nextProgress);
            }
          },
          onVerticalDragEnd: (details) {
            if (settling) return;
            final velocity = -(details.primaryVelocity ?? 0) / viewportHeight;
            final commit =
                progress.abs() > .18 ||
                (progress.abs() > .04 &&
                    velocity.abs() > .7 &&
                    velocity.sign == progress.sign);
            settle(commit);
          },
          onVerticalDragCancel: () {
            if (!settling) settle(false);
          },
          child: ClipRect(
            child: Stack(
              fit: StackFit.expand,
              children: [
                if (showNext)
                  IgnorePointer(
                    child: ExcludeSemantics(
                      child: Transform.translate(
                        offset: Offset(
                          0,
                          direction * (1 - amount) * viewportHeight * .17,
                        ),
                        child: Transform.scale(
                          scale: .965 + amount * .035,
                          child: Opacity(
                            opacity: .75 + amount * .25,
                            child: widget.itemBuilder(next),
                          ),
                        ),
                      ),
                    ),
                  ),
                Transform.translate(
                  offset: Offset(0, -progress * viewportHeight * .76),
                  child: Transform.rotate(
                    angle: -progress * .01,
                    child: Transform.scale(
                      scale: 1 - amount * .045,
                      child: widget.itemBuilder(index),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      );
    },
  );
}

class BriefCard extends StatelessWidget {
  const BriefCard({
    super.key,
    required this.item,
    required this.saved,
    required this.onSave,
    required this.onShare,
    required this.onSource,
  });
  final Map<String, dynamic> item;
  final bool saved;
  final VoidCallback onSave, onShare, onSource;

  void showDetails(BuildContext context) {
    Widget row(IconData icon, String title, String value) => Padding(
      padding: const EdgeInsets.symmetric(vertical: 13),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: clay, size: 21),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: const TextStyle(fontWeight: FontWeight.w700),
                ),
                const SizedBox(height: 3),
                Text(value, style: const TextStyle(color: muted, height: 1.35)),
              ],
            ),
          ),
        ],
      ),
    );
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      backgroundColor: const Color(0xFFFFFDF9),
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(22)),
      ),
      builder: (sheetContext) => SafeArea(
        top: false,
        child: ConstrainedBox(
          constraints: BoxConstraints(
            maxHeight: MediaQuery.sizeOf(sheetContext).height * .82,
          ),
          child: SingleChildScrollView(
            padding: const EdgeInsets.fromLTRB(20, 2, 20, 24),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                const Text(
                  'Impact & next steps',
                  style: TextStyle(
                    fontFamily: 'serif',
                    fontSize: 27,
                    color: ink,
                  ),
                ),
                const SizedBox(height: 5),
                const Text(
                  'A practical readout for this briefing.',
                  style: TextStyle(color: muted),
                ),
                const SizedBox(height: 14),
                const Divider(),
                row(
                  Icons.info_outline,
                  'Why it matters',
                  item['why_it_matters']?.toString() ?? '',
                ),
                const Divider(),
                row(
                  Icons.check_box_outlined,
                  'What to check',
                  item['next_action']?.toString() ?? '',
                ),
                if ((item['source_label']?.toString() ?? '').isNotEmpty) ...[
                  const Divider(),
                  Text(
                    'Source: ${item['source_label']}',
                    style: const TextStyle(
                      color: clay,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ],
                const SizedBox(height: 17),
                SizedBox(
                  width: double.infinity,
                  child: FilledButton(
                    onPressed: () => Navigator.pop(sheetContext),
                    child: const Text('Back to briefing'),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget mediaIcon(
    IconData icon,
    String label,
    VoidCallback action,
    bool compact,
  ) => Semantics(
    button: true,
    label: label,
    child: Material(
      color: Colors.white.withValues(alpha: .94),
      borderRadius: BorderRadius.circular(8),
      child: InkWell(
        onTap: action,
        borderRadius: BorderRadius.circular(8),
        child: SizedBox(
          width: compact ? 31 : 35,
          height: compact ? 31 : 35,
          child: Icon(icon, size: compact ? 18 : 20, color: clay),
        ),
      ),
    ),
  );

  @override
  Widget build(BuildContext context) => LayoutBuilder(
    builder: (context, size) {
      final compact = size.maxHeight < 560, tiny = size.maxHeight < 430;
      final fictional = item['fictional'] == true;
      final technology = item['technology']?.toString() ?? '';
      final source = fictional
          ? 'Fictional example'
          : item['source_label']?.toString() ?? 'Official source';
      return Container(
        padding: EdgeInsets.all(
          tiny
              ? 9
              : compact
              ? 12
              : 16,
        ),
        decoration: BoxDecoration(
          color: Colors.white,
          border: Border.all(color: line),
          borderRadius: BorderRadius.circular(15),
          boxShadow: const [
            BoxShadow(
              color: Color(0x10000000),
              blurRadius: 14,
              offset: Offset(0, 4),
            ),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              child: FittedBox(
                fit: BoxFit.scaleDown,
                alignment: Alignment.topLeft,
                child: SizedBox(
                  width:
                      size.maxWidth -
                      2 *
                          (tiny
                              ? 9
                              : compact
                              ? 12
                              : 16),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      SizedBox(
                        height: tiny
                            ? 76
                            : compact
                            ? 98
                            : 124,
                        width: double.infinity,
                        child: ClipRRect(
                          borderRadius: BorderRadius.circular(10),
                          child: Stack(
                            children: [
                              Positioned.fill(
                                child: DecoratedBox(
                                  decoration: const BoxDecoration(
                                    gradient: LinearGradient(
                                      colors: [
                                        Color(0xFFF9F4EE),
                                        Color(0xFFF1DFD0),
                                      ],
                                    ),
                                  ),
                                ),
                              ),
                              Positioned(
                                right: 25,
                                top: 0,
                                bottom: 0,
                                child: Opacity(
                                  opacity: .22,
                                  child: techMark(
                                    technology,
                                    size: tiny
                                        ? 70
                                        : compact
                                        ? 95
                                        : 120,
                                  ),
                                ),
                              ),
                              Positioned(
                                top: 7,
                                left: 7,
                                right: 7,
                                child: Row(
                                  children: [
                                    Expanded(
                                      child: Container(
                                        padding: const EdgeInsets.symmetric(
                                          horizontal: 7,
                                          vertical: 6,
                                        ),
                                        decoration: BoxDecoration(
                                          color: Colors.white.withValues(
                                            alpha: .94,
                                          ),
                                          borderRadius: BorderRadius.circular(
                                            7,
                                          ),
                                        ),
                                        child: Text(
                                          source,
                                          maxLines: 1,
                                          overflow: TextOverflow.ellipsis,
                                          style: const TextStyle(
                                            fontSize: 10,
                                            color: ink,
                                            fontWeight: FontWeight.w600,
                                          ),
                                        ),
                                      ),
                                    ),
                                    const SizedBox(width: 6),
                                    mediaIcon(
                                      saved
                                          ? Icons.bookmark
                                          : Icons.bookmark_outline,
                                      saved
                                          ? 'Remove saved briefing'
                                          : 'Save briefing',
                                      onSave,
                                      compact,
                                    ),
                                    const SizedBox(width: 5),
                                    mediaIcon(
                                      Icons.ios_share_outlined,
                                      'Share briefing',
                                      onShare,
                                      compact,
                                    ),
                                  ],
                                ),
                              ),
                              Positioned(
                                left: 7,
                                bottom: 7,
                                child: Semantics(
                                  button: true,
                                  label: 'Impact and next steps',
                                  child: Material(
                                    color: clay,
                                    borderRadius: BorderRadius.circular(8),
                                    elevation: 3,
                                    child: InkWell(
                                      onTap: () => showDetails(context),
                                      borderRadius: BorderRadius.circular(8),
                                      child: Padding(
                                        padding: EdgeInsets.symmetric(
                                          horizontal: tiny ? 6 : 9,
                                          vertical: tiny ? 4 : 6,
                                        ),
                                        child: Row(
                                          mainAxisSize: MainAxisSize.min,
                                          children: [
                                            const Icon(
                                              Icons.info_outline,
                                              size: 19,
                                              color: Colors.white,
                                            ),
                                            const SizedBox(width: 5),
                                            Text(
                                              tiny
                                                  ? 'Details'
                                                  : 'Impact & actions',
                                              style: TextStyle(
                                                color: Colors.white,
                                                fontSize: tiny ? 10 : 11,
                                                fontWeight: FontWeight.w700,
                                              ),
                                            ),
                                            const SizedBox(width: 4),
                                            const Icon(
                                              Icons.arrow_outward,
                                              size: 14,
                                              color: Colors.white,
                                            ),
                                          ],
                                        ),
                                      ),
                                    ),
                                  ),
                                ),
                              ),
                              Positioned(
                                right: 7,
                                bottom: 7,
                                child: item['source_url'] == null
                                    ? Container(
                                        padding: const EdgeInsets.symmetric(
                                          horizontal: 9,
                                          vertical: 6,
                                        ),
                                        decoration: BoxDecoration(
                                          color: muted,
                                          borderRadius: BorderRadius.circular(
                                            7,
                                          ),
                                        ),
                                        child: const Text(
                                          'Sample only',
                                          style: TextStyle(
                                            color: Colors.white,
                                            fontSize: 10,
                                          ),
                                        ),
                                      )
                                    : SizedBox(
                                        height: tiny ? 28 : 32,
                                        child: FilledButton.icon(
                                          onPressed: onSource,
                                          icon: const Icon(
                                            Icons.open_in_new,
                                            size: 14,
                                          ),
                                          label: const Text(
                                            'Read source',
                                            style: TextStyle(fontSize: 11),
                                          ),
                                          style: FilledButton.styleFrom(
                                            backgroundColor: clay,
                                            padding: const EdgeInsets.symmetric(
                                              horizontal: 10,
                                            ),
                                            minimumSize: Size.zero,
                                            tapTargetSize: MaterialTapTargetSize
                                                .shrinkWrap,
                                            shape: RoundedRectangleBorder(
                                              borderRadius:
                                                  BorderRadius.circular(7),
                                            ),
                                          ),
                                        ),
                                      ),
                              ),
                            ],
                          ),
                        ),
                      ),
                      SizedBox(
                        height: tiny
                            ? 6
                            : compact
                            ? 8
                            : 11,
                      ),
                      Text(
                        fictional
                            ? 'FICTIONAL SAMPLE · ${(item['type'] ?? 'UPDATE').toString().toUpperCase()}'
                            : (item['type'] ?? 'UPDATE')
                                  .toString()
                                  .toUpperCase(),
                        style: const TextStyle(
                          color: clay,
                          fontSize: 10,
                          fontWeight: FontWeight.w700,
                          letterSpacing: .6,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        item['title']?.toString() ?? '',
                        style: TextStyle(
                          fontFamily: 'serif',
                          fontSize: tiny
                              ? 18
                              : compact
                              ? 21
                              : 25,
                          height: 1.05,
                          fontWeight: FontWeight.w600,
                          color: ink,
                        ),
                      ),
                      SizedBox(
                        height: tiny
                            ? 4
                            : compact
                            ? 6
                            : 9,
                      ),
                      Text(
                        item['summary']?.toString() ?? '',
                        style: TextStyle(
                          fontSize: tiny
                              ? 11
                              : compact
                              ? 12
                              : 14,
                          height: 1.27,
                          color: ink,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ],
        ),
      );
    },
  );
}

class Settings extends StatefulWidget {
  const Settings({
    super.key,
    required this.api,
    required this.prefs,
    required this.catalog,
    required this.onReset,
  });
  final TechWatchApi api;
  final Map<String, dynamic> prefs;
  final Map<String, dynamic> catalog;
  final VoidCallback onReset;
  @override
  State<Settings> createState() => _SettingsState();
}

class _SettingsState extends State<Settings> {
  bool deleting = false;
  Future<void> deleteData() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete my data?'),
        content: const Text(
          'This removes your selected interests and saved briefings from the server and resets this app installation.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Delete', style: TextStyle(color: clay)),
          ),
        ],
      ),
    );
    if (confirmed != true) return;
    setState(() => deleting = true);
    try {
      await widget.api.deleteMyData();
      if (mounted) {
        Navigator.pop(context);
        widget.onReset();
      }
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Deletion failed. Check connection and retry.'),
          ),
        );
      }
    } finally {
      if (mounted) setState(() => deleting = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(
      title: const Text(
        'Settings',
        style: TextStyle(fontFamily: 'serif', fontSize: 25),
      ),
    ),
    body: ListView(
      children: [
        const Padding(
          padding: EdgeInsets.fromLTRB(18, 18, 18, 10),
          child: Brand(width: 185),
        ),
        const ListTile(
          title: Text('TechWatch'),
          subtitle: Text('Practical technical briefings for builders.'),
        ),
        const Divider(),
        ListTile(
          leading: const Icon(Icons.layers_outlined, color: clay),
          title: const Text('Your stack'),
          subtitle: Text(
            '${strings(widget.prefs['follows']).length} technologies followed',
          ),
          trailing: const Icon(Icons.chevron_right),
          onTap: () async {
            final updated = await Navigator.push<bool>(
              context,
              MaterialPageRoute(
                builder: (_) => StackEditor(
                  api: widget.api,
                  prefs: widget.prefs,
                  catalog: widget.catalog,
                ),
              ),
            );
            if (updated == true && mounted) setState(() {});
          },
        ),
        ListTile(
          leading: const Icon(Icons.notifications_none, color: clay),
          title: const Text('Alerts'),
          subtitle: const Text('In-app updates only. No device notifications.'),
        ),
        ListTile(
          leading: const Icon(Icons.monitor_heart_outlined, color: clay),
          title: const Text('Source health'),
          subtitle: const Text('Official feed availability and last checks'),
          trailing: const Icon(Icons.chevron_right),
          onTap: () => Navigator.push(
            context,
            MaterialPageRoute(builder: (_) => SourceHealth(api: widget.api)),
          ),
        ),
        const Divider(),
        ListTile(
          leading: const Icon(Icons.privacy_tip_outlined, color: clay),
          title: const Text('Privacy policy'),
          trailing: const Icon(Icons.open_in_new, size: 17),
          onTap: () => launchUrl(
            Uri.parse('$apiBase/privacy'),
            mode: LaunchMode.externalApplication,
          ),
        ),
        ListTile(
          leading: const Icon(Icons.delete_outline, color: clay),
          title: const Text('Delete my data'),
          subtitle: const Text(
            'Remove preferences and saved briefings from this installation',
          ),
          onTap: deleting ? null : deleteData,
        ),
        const Padding(
          padding: EdgeInsets.all(18),
          child: Text(
            'Briefings are summaries of public sources. Open the official source to verify details before acting. Fictional examples are clearly marked.',
            style: TextStyle(color: muted, fontSize: 12),
          ),
        ),
      ],
    ),
  );
}

class StackEditor extends StatefulWidget {
  const StackEditor({
    super.key,
    required this.api,
    required this.prefs,
    required this.catalog,
  });
  final TechWatchApi api;
  final Map<String, dynamic> prefs, catalog;
  @override
  State<StackEditor> createState() => _StackEditorState();
}

class _StackEditorState extends State<StackEditor> {
  late final selected = strings(widget.prefs['follows']).toSet();
  String search = '';
  bool saving = false;
  Future<void> save() async {
    if (saving) return;
    setState(() => saving = true);
    try {
      final update = <String, dynamic>{
        ...widget.prefs,
        'follows': selected.toList(),
      };
      final value = Map<String, dynamic>.from(
        await widget.api.request('/v1/preferences', method: 'PUT', body: update)
            as Map,
      );
      await widget.api.storage.setString('preferences', jsonEncode(value));
      widget.prefs.addAll(value);
      if (mounted) Navigator.pop(context, true);
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Could not save your stack. Try again.'),
          ),
        );
      }
    } finally {
      if (mounted) setState(() => saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final options = strings(widget.catalog['technologies'])
        .where((item) => item.toLowerCase().contains(search.toLowerCase()))
        .toList();
    return Scaffold(
      appBar: AppBar(
        title: const Text(
          'Follow your stack',
          style: TextStyle(fontFamily: 'serif', fontSize: 24),
        ),
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(18),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'Select the technologies you use or evaluate.',
                style: TextStyle(color: muted),
              ),
              const SizedBox(height: 12),
              TextField(
                onChanged: (value) => setState(() => search = value),
                decoration: InputDecoration(
                  prefixIcon: const Icon(Icons.search),
                  hintText: 'Search technologies',
                  filled: true,
                  fillColor: Colors.white,
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
              ),
              const SizedBox(height: 12),
              Expanded(
                child: GridView.builder(
                  itemCount: options.length,
                  gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                    crossAxisCount: 2,
                    crossAxisSpacing: 9,
                    mainAxisSpacing: 9,
                    childAspectRatio: 1.65,
                  ),
                  itemBuilder: (_, i) => ChoiceTile(
                    label: options[i],
                    selected: selected.contains(options[i]),
                    tap: () => setState(
                      () => selected.contains(options[i])
                          ? selected.remove(options[i])
                          : selected.add(options[i]),
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 10),
              ActionButton(
                'Save ${selected.length} technologies',
                saving ? null : save,
                icon: Icons.check,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class SourceHealth extends StatefulWidget {
  const SourceHealth({super.key, required this.api});
  final TechWatchApi api;
  @override
  State<SourceHealth> createState() => _SourceHealthState();
}

class _SourceHealthState extends State<SourceHealth> {
  List<Map<String, dynamic>> sources = [];
  bool loading = true;
  String? error;
  @override
  void initState() {
    super.initState();
    load();
  }

  Future<void> load() async {
    setState(() {
      loading = true;
      error = null;
    });
    try {
      final data = await widget.api.getMap('/v1/source-health');
      if (mounted) {
        setState(() {
          sources = records(data['items']);
          loading = false;
        });
      }
    } catch (_) {
      if (mounted) {
        setState(() {
          loading = false;
          error = 'Could not load source health.';
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(
      title: const Text(
        'Source health',
        style: TextStyle(fontFamily: 'serif', fontSize: 25),
      ),
    ),
    body: loading
        ? const Center(child: CircularProgressIndicator(color: clay))
        : error != null
        ? Center(
            child: TextButton(onPressed: load, child: Text('$error Retry')),
          )
        : RefreshIndicator(
            onRefresh: load,
            child: ListView(
              children: [
                const Padding(
                  padding: EdgeInsets.all(18),
                  child: Text(
                    'Availability of curated official sources. A healthy source does not guarantee every update is published.',
                    style: TextStyle(color: muted),
                  ),
                ),
                for (final source in sources)
                  ListTile(
                    leading: techMark(source['technology']?.toString() ?? ''),
                    title: Text(source['technology']?.toString() ?? 'Source'),
                    subtitle: Text(
                      source['url']?.toString() ?? '',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    trailing: Text(
                      source['status']?.toString() ?? 'unknown',
                      style: TextStyle(
                        color: source['status'] == 'healthy'
                            ? const Color(0xFF2B7B59)
                            : clay,
                        fontSize: 12,
                      ),
                    ),
                  ),
              ],
            ),
          ),
  );
}
