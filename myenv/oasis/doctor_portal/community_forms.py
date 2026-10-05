from django import forms
from .models import CommunityPost, CommunityReply


class CommunityPostForm(forms.ModelForm):
    media = forms.FileField(required=False, widget=forms.FileInput(attrs={'accept': 'image/jpeg,image/png,image/webp,video/mp4,video/webm'}))

    def clean_media(self):
        upload = self.cleaned_data.get('media')
        if not upload:
            return upload
        if upload.size > 20 * 1024 * 1024:
            raise forms.ValidationError('Choose a file smaller than 20 MB.')
        self.media_type = ''
        header = upload.read(32)
        upload.seek(0)
        name = upload.name.lower()
        if (header.startswith(b'\xff\xd8\xff') and name.endswith(('.jpg', '.jpeg'))
                or header.startswith(b'\x89PNG\r\n\x1a\n') and name.endswith('.png')
                or header[:4] == b'RIFF' and header[8:12] == b'WEBP' and name.endswith('.webp')):
            self.media_type = 'image'
        elif header[4:8] == b'ftyp' and name.endswith('.mp4'):
            self.media_type = 'video'
        elif header[:4] == b'\x1aE\xdf\xa3' and name.endswith('.webm'):
            self.media_type = 'video'
        else:
            raise forms.ValidationError('Upload a valid JPG, PNG, WebP, MP4, or WebM file.')
        return upload

    class Meta:
        model = CommunityPost
        fields = ('title', 'topic', 'body', 'media')
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'Give your discussion a title'}),
            'body': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Share an experience, ask a question, or start a conversation…'}),
        }


class CommunityReplyForm(forms.ModelForm):
    class Meta:
        model = CommunityReply
        fields = ('body',)
