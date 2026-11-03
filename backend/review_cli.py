"""Local operator review. Run inside the API container, never from the public UI."""
import argparse
import json

from backend.db import migrate
from backend.engine import edit_brief, review_decision, review_queue, draft_detail


def main():
    parser = argparse.ArgumentParser(description='Review source-backed TechWatch drafts')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('queue')
    show = sub.add_parser('show')
    show.add_argument('id')
    edit = sub.add_parser('edit')
    edit.add_argument('id')
    for field in ('title', 'summary', 'why_it_matters', 'next_action'):
        edit.add_argument('--' + field.replace('_', '-'))
    for action in ('publish', 'reject'):
        command = sub.add_parser(action)
        command.add_argument('id')
    args = parser.parse_args()
    migrate()
    if args.command == 'queue':
        result = review_queue()
    elif args.command == 'show':
        result = draft_detail(args.id)
    elif args.command == 'edit':
        changes = {field: getattr(args, field) for field in ('title', 'summary', 'why_it_matters', 'next_action')
                   if getattr(args, field) is not None}
        result = edit_brief(args.id, changes, actor='local-review-cli')
    else:
        result = review_decision(args.id, args.command, actor='local-review-cli')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
