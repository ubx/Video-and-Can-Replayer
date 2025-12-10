from kivy.properties import ListProperty
from kivy.uix.videoplayer import VideoPlayer, VideoPlayerAnnotation
from kivy.resources import resource_find


class VideoPlayer2(VideoPlayer):
    def __init__(self, **kwargs):
        # Ensure a safe thumbnail is provided before the base class initializes
        # so the internal Image widget never attempts to load the MP4 as an Image.
        thumb = resource_find('data/logo/kivy-icon-128.png') or resource_find('data/logo/kivy-icon-512.png')
        if thumb and (not kwargs.get('thumbnail')):
            kwargs['thumbnail'] = thumb
        super().__init__(**kwargs)

    def _load_annotations(self):
        pass

    def add_annotation(self, annotation):
        self._annotations_labels.append(VideoPlayerAnnotation(annotation=annotation))
