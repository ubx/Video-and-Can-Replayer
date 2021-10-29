from kivy.properties import ListProperty
from kivy.uix.videoplayer import VideoPlayer, VideoPlayerAnnotation


class VideoPlayer2(VideoPlayer):
    pass

    def _load_annotations(self):
        pass

    def add_annotation(self, annotation):
        self._annotations_labels.append(VideoPlayerAnnotation(annotation=annotation))
