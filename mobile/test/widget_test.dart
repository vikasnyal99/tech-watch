import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:techwatch/main.dart';

void main() {
  testWidgets('onboarding choice has a selected state', (tester) async {
    var selected = false;
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: ChoiceTile(
            label: 'Cloud infrastructure',
            selected: selected,
            tap: () => selected = true,
          ),
        ),
      ),
    );
    await tester.tap(find.text('Cloud infrastructure'));
    expect(selected, isTrue);
  });

  testWidgets('briefing card keeps its actions visible in a phone viewport', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(390, 640);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    final item = <String, dynamic>{
      'id': 'example',
      'type': 'release',
      'technology': 'Kubernetes',
      'title': 'Kubernetes release: what platform teams should review',
      'summary': 'This release changes supported versions and removes older APIs used by some workloads. Platform teams should review upgrade prerequisites, check add-on compatibility, and compare cluster behavior with the official release notes before rollout. The rollout plan should account for control plane, node, networking and storage components.',
      'why_it_matters': 'Clusters and add-ons using removed APIs may need changes before a safe upgrade.',
      'next_action': 'Inventory API usage and test the upgrade in a non-production cluster.',
      'source_label': 'Official Kubernetes release notes',
      'source_url': 'https://example.com',
      'fictional': false,
    };
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SafeArea(
            child: SizedBox(
              height: 400,
              child: BriefCard(
                item: item,
                saved: false,
                onSave: () {},
                onShare: () {},
                onSource: () {},
              ),
            ),
          ),
        ),
      ),
    );
    expect(find.text('Read source'), findsOneWidget);
    expect(find.byIcon(Icons.bookmark_outline), findsOneWidget);
    expect(find.byIcon(Icons.ios_share_outlined), findsOneWidget);
    expect(find.text('Details'), findsOneWidget);
    await tester.tap(find.text('Details'));
    await tester.pumpAndSettle();
    expect(find.text('Impact & next steps'), findsOneWidget);
    expect(find.text('Why it matters'), findsOneWidget);
    expect(find.text('What to check'), findsOneWidget);
    expect(
      find.textContaining('This release changes supported versions'),
      findsOneWidget,
    );
    expect(tester.takeException(), isNull);
  });

  testWidgets(
    'editorial pager follows a swipe and snaps back from a short drag',
    (tester) async {
      final items = <Map<String, dynamic>>[
        {'id': 'first'},
        {'id': 'second'},
      ];
      var current = 0;
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: SizedBox(
              height: 400,
              child: EditorialPager(
                items: items,
                initialIndex: 0,
                reducedMotion: false,
                onPageChanged: (value) => current = value,
                itemBuilder: (index) => Center(child: Text(items[index]['id'])),
              ),
            ),
          ),
        ),
      );
      await tester.drag(find.byType(EditorialPager), const Offset(0, -180));
      await tester.pumpAndSettle();
      expect(current, 1);
      expect(find.text('second'), findsOneWidget);
      await tester.timedDrag(
        find.byType(EditorialPager),
        const Offset(0, 50),
        const Duration(milliseconds: 400),
      );
      await tester.pumpAndSettle();
      expect(current, 1);
      expect(find.text('first'), findsNothing);
    },
  );

  testWidgets('reduced motion changes cards immediately', (tester) async {
    var current = 0;
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SizedBox(
            height: 400,
            child: EditorialPager(
              items: const [
                {'id': 'first'},
                {'id': 'second'},
              ],
              initialIndex: 0,
              reducedMotion: true,
              onPageChanged: (value) => current = value,
              itemBuilder: (index) => Center(child: Text('card $index')),
            ),
          ),
        ),
      ),
    );
    await tester.drag(find.byType(EditorialPager), const Offset(0, -180));
    await tester.pump();
    expect(current, 1);
    expect(find.text('card 1'), findsOneWidget);
  });
}
