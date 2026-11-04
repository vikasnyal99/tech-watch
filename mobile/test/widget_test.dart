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
      'summary': 'This release changes supported versions and removes older APIs used by some workloads. Platform teams should review upgrade prerequisites, check add-on compatibility, and compare cluster behavior with the official release notes before rollout.',
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
    expect(
      find.textContaining('This release changes supported versions'),
      findsOneWidget,
    );
    expect(tester.takeException(), isNull);
  });
}
