from typing import Dict, List, Union, Optional

from datasets import Dataset
from evaluate import (Evaluator, TokenClassificationEvaluator)

from zshot.utils.alignment_utils import AlignmentMode, filter_overlapping_spans
from zshot.utils.data_models import Span


class ZeroShotTokenClassificationEvaluator(TokenClassificationEvaluator):

    def __init__(self, task="token-classification", default_metric_name=None,
                 mode: Optional[str] = 'span', alignment_mode=AlignmentMode.expand,
                 entity_mapper: Optional[Dict[str, str]] = None):
        super().__init__(task, default_metric_name)
        self.alignment_mode = alignment_mode
        self.mode = mode
        self.entity_mapper = entity_mapper

    def process_label(self, label):
        if label != "O":
            if self.entity_mapper is not None:
                label_prefix = label[:2]
                label = label_prefix + self.entity_mapper[label[2:]]

        return f"B-{label[2:]}" if label.startswith("I-") and self.mode == 'token' else label

    def prepare_data(self, data: Union[str, Dataset], input_column: str, label_column: str, join_by: str):
        metric_inputs, pipeline_inputs = super().prepare_data(data, input_column, label_column, join_by)

        metric_inputs['references'] = [[self.process_label(label) for label in sent]
                                       for sent in metric_inputs['references']]

        return metric_inputs, pipeline_inputs

    def predictions_processor(self, predictions: List[List[Dict]], sentences: List[List[str]], join_by: str):
        predictions_pr = []
        for prediction, words in zip(predictions, sentences):
            words_offsets = self.words_to_offsets(words, join_by)
            prediction_spans = list(map(lambda p: Span(p['start'], p['end'] - 1, p['entity'],
                                                       p['score'] if 'score' in p else None), prediction))
            filter_dict = filter_overlapping_spans(prediction_spans,
                                                   words,
                                                   tokens_offsets=words_offsets,
                                                   alignment_mode=self.alignment_mode,
                                                   evaluation_mode=self.mode,
                                                   return_dict=True)
            predictions_pr.append(filter_dict['bio'])
        return {"predictions": predictions_pr}

    def prepare_pipeline(
            self,
            model_or_pipeline,  # noqa: F821
            tokenizer=None,  # noqa: F821
            feature_extractor=None,  # noqa: F821
            device: int = None,
    ):
        pipe = super(TokenClassificationEvaluator, self).prepare_pipeline(model_or_pipeline, tokenizer,
                                                                          feature_extractor, device)
        return pipe


class MentionsExtractorEvaluator(ZeroShotTokenClassificationEvaluator):
    def __init__(self, task="token-classification", default_metric_name=None,
                 mode: Optional[str] = 'span', alignment_mode=AlignmentMode.expand,
                 entity_mapper: Optional[Dict[str, str]] = None):
        super().__init__(task, default_metric_name, alignment_mode=alignment_mode)
        self.mode = mode
        self.entity_mapper = entity_mapper

    def process_label(self, label):
        if label != "O":
            if self.entity_mapper is not None:
                label_prefix = label[:2]
                label = label_prefix + self.entity_mapper[label[2:]]
            if (label.startswith("B-") or label.startswith("I-")) and self.mode == 'span':
                label = label[:2] + "MENTION"
            else:
                label = "B-MENTION"

        return label

    def prepare_data(self, data: Union[str, Dataset], input_column: str, label_column: str, join_by: str):
        metric_inputs, pipeline_inputs = super().prepare_data(data, input_column, label_column, join_by)

        metric_inputs['references'] = [[self.process_label(label) for label in sent]
                                       for sent in metric_inputs['references']]

        return metric_inputs, pipeline_inputs


class RelationExtractorEvaluator(Evaluator):
    def __init__(self, task="relation-extraction", default_metric_name=None):
        super().__init__(task, default_metric_name)

    def predictions_processor(self, predictions: List[List[Dict]], sentences: List[List[str]]):
        return {"predictions": predictions}

    def prepare_pipeline(
            self,
            model_or_pipeline,  # noqa: F821
            tokenizer=None,  # noqa: F821
            feature_extractor=None,  # noqa: F821
            device: int = None,
    ):
        pipe = super().prepare_pipeline(model_or_pipeline)
        return pipe
