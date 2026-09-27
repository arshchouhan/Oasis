"""Private patient tasks and notes for the right-hand panel."""
import json

from django.http import JsonResponse
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_http_methods

from .models import PatientNote, PatientTask, PatientTaskList, User


@require_http_methods(['GET', 'POST'])
def workspace(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Please sign in again.'}, status=401)
    if request.user.account_type != User.AccountType.PATIENT:
        return JsonResponse({'error': 'Patient access required.'}, status=403)
    lists = PatientTaskList.objects.filter(owner=request.user)
    tasks = PatientTask.objects.filter(task_list__owner=request.user)
    notes = PatientNote.objects.filter(owner=request.user)
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            if not isinstance(data, dict):
                raise ValueError('Invalid request.')
            action = data.get('action')

            def text(key, limit, required=False):
                value = data.get(key, '')
                if not isinstance(value, str) or len(value) > limit:
                    raise ValueError(f'{key.capitalize()} must be text of at most {limit} characters.')
                value = value.strip()
                if required and not value:
                    raise ValueError(f'Enter a {key}.')
                return value

            def owned(query, key='id'):
                try:
                    item = query.filter(pk=int(data.get(key))).first()
                except (ValueError, TypeError):
                    item = None
                if item is None:
                    raise ValueError('This item is no longer available.')
                return item

            if action == 'create_list':
                PatientTaskList.objects.create(owner=request.user, name=text('name', 80, True))
            elif action == 'save_task':
                title = text('title', 200, True)
                description = text('notes', 5000)
                raw_date = text('due_date', 10)
                due_date = parse_date(raw_date) if raw_date else None
                if raw_date and due_date is None:
                    raise ValueError('Choose a valid due date.')
                task = owned(tasks) if data.get('id') else PatientTask(task_list=owned(lists, 'list_id'))
                task.title, task.notes, task.due_date = title, description, due_date
                task.save()
            elif action == 'complete_task':
                if not isinstance(data.get('completed'), bool):
                    raise ValueError('Invalid completion value.')
                task = owned(tasks)
                task.completed = data['completed']
                task.save(update_fields=['completed'])
            elif action == 'delete_task':
                owned(tasks).delete()
            elif action == 'save_note':
                title, body = text('title', 200, True), text('body', 5000)
                note = owned(notes) if data.get('id') else PatientNote(owner=request.user)
                note.title, note.body = title, body
                note.save()
            elif action == 'delete_note':
                owned(notes).delete()
            else:
                raise ValueError('Unknown action.')
        except (ValueError, TypeError, UnicodeDecodeError):
            return JsonResponse({'error': 'Could not save. Check the fields and make sure this item is yours.'}, status=400)
    return JsonResponse({
        'lists': list(lists.values('id', 'name')),
        'tasks': list(tasks.values('id', 'task_list_id', 'title', 'notes', 'due_date', 'completed')),
        'notes': list(notes.values('id', 'title', 'body', 'updated_at')),
    })
