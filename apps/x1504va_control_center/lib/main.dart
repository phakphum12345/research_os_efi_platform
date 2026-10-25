import 'package:flutter/material.dart';

void main() => runApp(const ResearchPlatformApp());

class ResearchPlatformApp extends StatelessWidget {
  const ResearchPlatformApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Research OS Control Center',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        useMaterial3: true,
        colorSchemeSeed: Colors.indigo,
        scaffoldBackgroundColor: const Color(0xFFF6F7FB),
      ),
      home: const ControlCenterPage(),
    );
  }
}

class ControlCenterPage extends StatefulWidget {
  const ControlCenterPage({super.key});

  @override
  State<ControlCenterPage> createState() => _ControlCenterPageState();
}

class _ControlCenterPageState extends State<ControlCenterPage> {
  int _selectedIndex = 0;
  String _selectedPlatform = 'Auto-detect';
  String _notice = 'Ready to inspect this environment';

  static const _destinations = <({String label, IconData icon})>[
    (label: 'Overview', icon: Icons.dashboard_outlined),
    (label: 'Discovery', icon: Icons.manage_search),
    (label: 'Platforms', icon: Icons.devices_other),
    (label: 'Evidence', icon: Icons.fact_check_outlined),
    (label: 'Installer', icon: Icons.system_update_alt),
  ];

  static const _platforms = <String>[
    'Auto-detect',
    'Windows',
    'Linux',
    'macOS',
    'FreeBSD',
    'OpenBSD',
    'NetBSD',
    'Other / future platform',
  ];

  void _showReadOnlyPlan() {
    showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Read-only discovery'),
        content: const Text(
          'This screen is the control-center UI. The live discovery adapter '
          'is not connected to this Flutter app yet, so no scan has run.\n\n'
          'Planned sequence:\n'
          '1. Identify the current platform and hardware.\n'
          '2. Read available firmware and boot metadata without changing it.\n'
          '3. Record unavailable fields as unknown.\n'
          '4. Save evidence before matching an installer.\n\n'
          'No firmware, EFI/ESP, boot entries, disks, or security settings '
          'will be changed by this preview.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Close'),
          ),
        ],
      ),
    );
  }

  void _showActionDetails(String action) {
    setState(() => _notice = '$action selected · runtime connection pending');
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          '$action: UI action is ready, but its runtime adapter is not connected yet.',
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Research OS Control Center'),
        actions: [
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12),
            child: Center(
              child: Chip(
                avatar: const Icon(Icons.shield_outlined, size: 18),
                label: const Text('Read-only by default'),
              ),
            ),
          ),
        ],
      ),
      body: LayoutBuilder(
        builder: (context, constraints) {
          final compact = constraints.maxWidth < 760;
          final content = _buildContent(context);
          if (compact) {
            return Column(
              children: [
                Expanded(child: content),
                NavigationBar(
                  selectedIndex: _selectedIndex,
                  onDestinationSelected: (index) =>
                      setState(() => _selectedIndex = index),
                  destinations: _destinations
                      .map((item) => NavigationDestination(
                            icon: Icon(item.icon),
                            label: item.label,
                          ))
                      .toList(),
                ),
              ],
            );
          }
          return Row(
            children: [
              NavigationRail(
                selectedIndex: _selectedIndex,
                onDestinationSelected: (index) =>
                    setState(() => _selectedIndex = index),
                labelType: NavigationRailLabelType.all,
                destinations: _destinations
                    .map((item) => NavigationRailDestination(
                          icon: Icon(item.icon),
                          label: Text(item.label),
                        ))
                    .toList(),
              ),
              const VerticalDivider(width: 1),
              Expanded(child: content),
            ],
          );
        },
      ),
    );
  }

  Widget _buildContent(BuildContext context) {
    final theme = Theme.of(context);
    return ListView(
      padding: const EdgeInsets.all(24),
      children: [
        Text(
          _destinations[_selectedIndex].label,
          style: theme.textTheme.headlineMedium?.copyWith(
            fontWeight: FontWeight.w700,
          ),
        ),
        const SizedBox(height: 8),
        Text(
          'A hardware- and operating-system-neutral workspace. '
          'Capabilities are reported from evidence, not assumed.',
          style: theme.textTheme.bodyLarge,
        ),
        const SizedBox(height: 20),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(18),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Target environment',
                  style: TextStyle(fontWeight: FontWeight.w700),
                ),
                const SizedBox(height: 8),
                DropdownButtonFormField<String>(
                  initialValue: _selectedPlatform,
                  decoration: const InputDecoration(
                    border: OutlineInputBorder(),
                    helperText:
                        'Auto-detect is recommended; unsupported targets stay explicitly unknown.',
                  ),
                  items: _platforms
                      .map((platform) => DropdownMenuItem(
                            value: platform,
                            child: Text(platform),
                          ))
                      .toList(),
                  onChanged: (value) {
                    if (value != null) {
                      setState(() => _selectedPlatform = value);
                    }
                  },
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 12),
        if (_selectedIndex == 0) ..._overviewCards(),
        if (_selectedIndex == 1) ..._discoveryCards(),
        if (_selectedIndex == 2) ..._platformCards(),
        if (_selectedIndex == 3) ..._evidenceCards(),
        if (_selectedIndex == 4) ..._installerCards(),
        const SizedBox(height: 12),
        Card(
          color: theme.colorScheme.surfaceContainerHighest,
          child: ListTile(
            leading: const Icon(Icons.info_outline),
            title: const Text('Current UI/runtime status'),
            subtitle: Text(_notice),
          ),
        ),
        const SizedBox(height: 8),
        const Text(
          'Safety boundary: this interface does not modify firmware, EFI/ESP, '
          'Secure Boot, BCD, boot entries, or disks. A UI status is not proof '
          'that hardware compatibility or boot success has been established.',
        ),
      ],
    );
  }

  List<Widget> _overviewCards() => [
        _actionCard(
          Icons.manage_search,
          'Read machine and boot environment',
          'Collect available hardware, OS, firmware and boot metadata.',
          'Read-only discovery',
          _showReadOnlyPlan,
        ),
        _actionCard(
          Icons.rule_outlined,
          'Analyze compatibility',
          'Separate proven capabilities, unsupported paths and unknowns.',
          'Review compatibility',
          () => _showActionDetails('Analyze compatibility'),
        ),
        _actionCard(
          Icons.system_update_alt,
          'Find a matching installer',
          'Match platform requirements and verify the trusted source.',
          'Find installer',
          () => setState(() => _selectedIndex = 4),
        ),
      ];

  List<Widget> _discoveryCards() => [
        _actionCard(
          Icons.memory,
          'Hardware discovery',
          'CPU, memory, graphics, storage, network and device identifiers.',
          'Prepare hardware scan',
          _showReadOnlyPlan,
        ),
        _actionCard(
          Icons.settings_input_component,
          'UEFI / EFI discovery',
          'Read available boot entries and inspect accessible EFI files only.',
          'Prepare UEFI / EFI read',
          _showReadOnlyPlan,
        ),
        _actionCard(
          Icons.computer,
          'Operating-system discovery',
          'Use the appropriate OS-owned provider for the detected platform.',
          'Select OS provider',
          () => setState(() => _selectedIndex = 2),
        ),
      ];

  List<Widget> _platformCards() => [
        _infoCard(Icons.window, 'Windows', 'Provider registered; live results depend on the Windows runtime.'),
        _infoCard(Icons.terminal, 'Linux', 'Provider registered; use Linux-owned discovery and runtime operations.'),
        _infoCard(Icons.laptop_mac, 'macOS', 'Provider registered; compatibility remains evidence-scoped.'),
        _infoCard(Icons.extension, 'Other and future platforms', 'Registry entries alone do not mean a provider is implemented.'),
      ];

  List<Widget> _evidenceCards() => [
        _infoCard(Icons.verified_outlined, 'Evidence manifest', 'Track source, hashes, collection time and integrity.'),
        _infoCard(Icons.fact_check_outlined, 'Compatibility findings', 'Report PROVEN, RESEARCH, UNSUPPORTED or UNKNOWN with reasons.'),
        _infoCard(Icons.history, 'Audit trail', 'Keep discovery and validation separate from human-approved actions.'),
      ];

  List<Widget> _installerCards() => [
        _actionCard(
          Icons.search,
          'Search compatible installers',
          'Use platform requirements and trusted-source metadata before selection.',
          'Prepare installer search',
          () => _showActionDetails('Search compatible installers'),
        ),
        _actionCard(
          Icons.fingerprint,
          'Verify installer integrity',
          'Check expected SHA-256 and source URL before any installation step.',
          'Prepare verification',
          () => _showActionDetails('Verify installer integrity'),
        ),
        _infoCard(Icons.pan_tool_alt_outlined, 'Human approval required', 'Downloading or installing is not triggered by this UI preview.'),
      ];

  Widget _actionCard(
    IconData icon,
    String title,
    String description,
    String buttonLabel,
    VoidCallback onPressed,
  ) =>
      Card(
        child: Padding(
          padding: const EdgeInsets.all(18),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(icon, size: 28),
              const SizedBox(height: 10),
              Text(title, style: const TextStyle(fontWeight: FontWeight.w700)),
              const SizedBox(height: 6),
              Text(description),
              const SizedBox(height: 12),
              Align(
                alignment: Alignment.centerLeft,
                child: FilledButton.icon(
                  onPressed: onPressed,
                  icon: const Icon(Icons.play_arrow),
                  label: Text(buttonLabel),
                ),
              ),
            ],
          ),
        ),
      );

  Widget _infoCard(IconData icon, String title, String description) =>
      Card(
        child: ListTile(
          leading: Icon(icon),
          title: Text(title),
          subtitle: Text(description),
        ),
      );
}
