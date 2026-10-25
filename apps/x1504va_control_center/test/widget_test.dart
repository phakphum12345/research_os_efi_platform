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
    expect(find.text('Other and future platforms'), findsOneWidget);
  });
}
