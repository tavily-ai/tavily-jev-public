"""Default company context for live competitor monitoring."""

DEFAULT_COMPANY = {
    'name': 'Forma',
    'description': 'A lightweight project management tool that helps small software teams plan work, track progress, and reduce manual coordination.',
    'audience': 'Product and engineering teams of 10–100 people.',
    'priorities': [
        {'id': 'ai', 'label': 'AI planning', 'detail': 'AI features that automate planning, task creation, and status updates.', 'importance': 'high'},
        {'id': 'pricing', 'label': 'Team pricing', 'detail': 'Per-seat pricing changes, free-plan limits, and whether AI costs extra.', 'importance': 'high'},
        {'id': 'integrations', 'label': 'Developer integrations', 'detail': 'New GitHub, Slack, and developer-tool integrations.', 'importance': 'watch'},
    ],
    'competitors': [
        {'name': 'Linear'},
        {'name': 'Asana'},
        {'name': 'ClickUp'},
    ],
}
