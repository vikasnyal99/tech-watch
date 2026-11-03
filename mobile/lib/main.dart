import 'dart:convert';

import 'package:flutter/material.dart';
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
              Icon(iconFor(label), color: clay, size: 25),
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
                      Image.asset(
                        'assets/branding/techwatch-monogram.png',
                        width: 88,
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
  final pager = PageController();
  final searchController = TextEditingController();
  static const sections = ['Feed', 'Your Stack', 'Trending', 'AI'];
  static const sectionIds = ['feed', 'stack', 'trending', 'ai'];
  @override
  void initState() {
    super.initState();
    refresh();
    loadSaved();
  }

  @override
  void dispose() {
    pager.dispose();
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
          if (mounted && pager.hasClients) pager.jumpToPage(0);
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

  void goSection(int value) {
    setState(() {
      section = value;
      topic = '';
    });
    refresh();
  }

  void goDestination(int value) {
    setState(() => destination = value);
    if (value == 2) loadSaved();
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
      destinations: const [
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
          onPressed: () => Navigator.of(context).push(
            MaterialPageRoute(
              builder: (_) => Settings(
                api: widget.api,
                prefs: widget.prefs,
                onReset: widget.onReset,
              ),
            ),
          ),
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
          onPressed: filterTopics,
          icon: const Icon(Icons.tune, size: 16),
          label: Text(
            topic.isEmpty ? 'All updates' : topic,
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
              if (pager.hasClients) pager.jumpToPage(i);
            });
          }),
        ),
      );
    }
    return PageView.builder(
      key: ValueKey('${sectionIds[section]}-$topic'),
      controller: pager,
      scrollDirection: Axis.vertical,
      itemCount: items.length,
      onPageChanged: (i) => setState(() => focus = i),
      itemBuilder: (_, i) => Padding(
        padding: const EdgeInsets.fromLTRB(12, 0, 12, 8),
        child: BriefCard(
          item: items[i],
          saved: saved.any((s) => s['id'] == items[i]['id']),
          onSave: () => bookmark(items[i]),
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
            child: Icon(
              iconFor(item['technology']?.toString() ?? ''),
              color: clay,
              size: 32,
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
                  onReset: widget.onReset,
                ),
              ),
            ),
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

class BriefCard extends StatelessWidget {
  const BriefCard({
    super.key,
    required this.item,
    required this.saved,
    required this.onSave,
    required this.onSource,
  });
  final Map<String, dynamic> item;
  final bool saved;
  final VoidCallback onSave, onSource;
  @override
  Widget build(BuildContext context) => LayoutBuilder(
    builder: (context, size) {
      final compact = size.maxHeight < 560;
      final title = item['title']?.toString() ?? '',
          summary = item['summary']?.toString() ?? '';
      final why = item['why_it_matters']?.toString() ?? '',
          action = item['next_action']?.toString() ?? '';
      final fictional = item['fictional'] == true;
      return Container(
        padding: EdgeInsets.all(compact ? 13 : 17),
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
            Container(
              height: compact ? 72 : 110,
              width: double.infinity,
              decoration: BoxDecoration(
                gradient: const LinearGradient(
                  colors: [Color(0xFFF9F4EE), Color(0xFFF1DFD0)],
                ),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Stack(
                children: [
                  Positioned(
                    right: 20,
                    top: 0,
                    bottom: 0,
                    child: Icon(
                      iconFor(item['technology']?.toString() ?? ''),
                      size: compact ? 63 : 95,
                      color: const Color(0x40B74420),
                    ),
                  ),
                  Positioned(
                    left: 14,
                    bottom: 13,
                    child: Text(
                      item['technology']?.toString() ?? '',
                      style: const TextStyle(
                        color: clay,
                        fontWeight: FontWeight.w700,
                        fontSize: 13,
                      ),
                    ),
                  ),
                ],
              ),
            ),
            SizedBox(height: compact ? 8 : 11),
            Text(
              fictional
                  ? 'FICTIONAL SAMPLE · ${(item['type'] ?? 'UPDATE').toString().toUpperCase()}'
                  : (item['type'] ?? 'UPDATE').toString().toUpperCase(),
              style: const TextStyle(
                color: clay,
                fontSize: 10,
                fontWeight: FontWeight.w700,
                letterSpacing: .6,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              title,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                fontFamily: 'serif',
                fontSize: compact ? 21 : 25,
                height: 1.05,
                fontWeight: FontWeight.w600,
                color: ink,
              ),
            ),
            SizedBox(height: compact ? 5 : 9),
            Text(
              summary,
              maxLines: compact ? 4 : 5,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                fontSize: compact ? 12 : 14,
                height: 1.29,
                color: ink,
              ),
            ),
            SizedBox(height: compact ? 8 : 14),
            Container(
              width: double.infinity,
              padding: EdgeInsets.all(compact ? 9 : 12),
              decoration: BoxDecoration(
                color: soft,
                borderRadius: BorderRadius.circular(9),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  insight(
                    Icons.lightbulb_outline,
                    'Why it matters',
                    why,
                    compact,
                  ),
                  SizedBox(height: compact ? 6 : 9),
                  insight(
                    Icons.check_box_outlined,
                    'What to check',
                    action,
                    compact,
                  ),
                ],
              ),
            ),
            const Spacer(),
            const Divider(color: line, height: 12),
            Text(
              fictional
                  ? 'Illustrative example — no live source'
                  : 'Source: ${item['source_label'] ?? 'Official publisher'}',
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(color: muted, fontSize: 11),
            ),
            SizedBox(height: compact ? 5 : 8),
            Row(
              children: [
                TextButton.icon(
                  onPressed: onSave,
                  icon: Icon(
                    saved ? Icons.bookmark : Icons.bookmark_outline,
                    size: 19,
                  ),
                  label: Text(saved ? 'Saved' : 'Save'),
                  style: TextButton.styleFrom(foregroundColor: ink),
                ),
                const Spacer(),
                if (item['source_url'] != null)
                  FilledButton(
                    onPressed: onSource,
                    style: FilledButton.styleFrom(
                      backgroundColor: clay,
                      padding: const EdgeInsets.symmetric(horizontal: 14),
                    ),
                    child: const Row(
                      children: [
                        Text('Read source'),
                        SizedBox(width: 5),
                        Icon(Icons.open_in_new, size: 15),
                      ],
                    ),
                  ),
              ],
            ),
          ],
        ),
      );
    },
  );
  Widget insight(IconData icon, String heading, String body, bool compact) =>
      Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: clay, size: compact ? 17 : 19),
          const SizedBox(width: 9),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  heading,
                  style: TextStyle(
                    fontWeight: FontWeight.w700,
                    fontSize: compact ? 11 : 12,
                  ),
                ),
                Text(
                  body,
                  maxLines: compact ? 2 : 3,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    fontSize: compact ? 11 : 12,
                    color: muted,
                    height: 1.2,
                  ),
                ),
              ],
            ),
          ),
        ],
      );
}

class Settings extends StatefulWidget {
  const Settings({
    super.key,
    required this.api,
    required this.prefs,
    required this.onReset,
  });
  final TechWatchApi api;
  final Map<String, dynamic> prefs;
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
                    leading: Icon(
                      iconFor(source['technology']?.toString() ?? ''),
                      color: clay,
                    ),
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
