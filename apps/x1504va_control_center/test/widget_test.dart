import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:x1504va_control_center/main.dart';

void main() {
  testWidgets('renders universal control center without a fixed device profile',
      (tester) async {
    await tester.pumpWidget(const ResearchPlatformApp());

    expect(find.text('Research OS Control Center'), findsOneWidget);
    expect(find.text('Target environment'), findsOneWidget);
    expect(find.text('Read-only by default'), findsOneWidget);
    expect(find.text('ASUS Vivobook X1504VA'), findsNothing);
  });

  testWidgets('discovery action clearly reports that live runtime is not connected',
      (tester) async {
    await tester.pumpWidget(const ResearchPlatformApp());

    await tester.tap(find.text('Read-only discovery'));
    await tester.pumpAndSettle();

    expect(find.text('Read-only discovery'), findsWidgets);
    expect(find.textContaining('live discovery adapter is not connected'),
        findsOneWidget);
  });

  testWidgets('platform navigation shows platform registry information',
      (tester) async {
    await tester.pumpWidget(const ResearchPlatformApp());

    await tester.tap(find.text('Platforms').first);
    await tester.pumpAndSettle();

    expect(find.text('Windows'), findsWidgets);
    expect(find.text('Linux'), findsWidgets);
    final futurePlatforms = find.text('Other and future platforms');
    await tester.scrollUntilVisible(
      futurePlatforms,
      250,
      scrollable: find.byType(Scrollable).first,
    );
    expect(futurePlatforms, findsOneWidget);
  });
  testWidgets('quick action buttons navigate to their workspaces', (tester) async {
    await tester.pumpWidget(const ResearchPlatformApp());

    expect(find.text('Read-only Discovery'), findsOneWidget);
    expect(find.text('View Evidence'), findsOneWidget);
    expect(find.text('Installer Research'), findsOneWidget);

    await tester.tap(find.text('View Evidence'));
    await tester.pumpAndSettle();
    expect(find.text('Evidence manifest'), findsOneWidget);

    await tester.tap(find.text('Installer Research'));
    await tester.pumpAndSettle();
    expect(find.text('Search compatible installers'), findsOneWidget);
  });

  testWidgets('discovery preview exposes an action to open Discovery', (tester) async {
    await tester.pumpWidget(const ResearchPlatformApp());

    await tester.tap(find.text('Read-only Discovery'));
    await tester.pumpAndSettle();

    expect(find.text('Open Discovery'), findsOneWidget);
    await tester.tap(find.text('Open Discovery'));
    await tester.pumpAndSettle();
    expect(find.text('Hardware discovery'), findsOneWidget);
  });

}
