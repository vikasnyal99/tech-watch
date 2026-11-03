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
    tester.view.physicalSize = const Size(390, 844);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    final item = <String, dynamic>{
      'id': 'example',
      'type': 'release',
      'technology': 'Kubernetes',
      'title': 'Kubernetes release: what platform teams should review',
      'summary': 'Review supported versions, API removals and upgrade prerequisites before changing clusters.',
      'why_it_matters': 'Compatibility may affect deployed workloads.',
      'next_action': 'Check release notes and test upgrades.',
      'source_label': 'Official Kubernetes release notes',
      'source_url': 'https://example.com',
      'fictional': false,
    };
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SafeArea(
            child: SizedBox(
              height: 620,
              child: BriefCard(
                item: item,
                saved: false,
                onSave: () {},
                onSource: () {},
              ),
            ),
          ),
        ),
      ),
    );
    expect(find.text('Read source'), findsOneWidget);
    expect(find.text('Save'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
