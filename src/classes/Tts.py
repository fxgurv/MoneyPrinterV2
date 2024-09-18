import os
import sys
import io
import warnings
from contextlib import redirect_stdout, redirect_stderr
from config import ROOT_DIR
from TTS.utils.manage import ModelManager
from TTS.utils.synthesizer import Synthesizer

class TTS:
    def __init__(self) -> None:
        site_packages = next((p for p in sys.path if 'site-packages' in p), None)

        if not site_packages:
            raise EnvironmentError("Could not find site-packages directory. Ensure that the TTS package is installed.")

        models_json_path = os.path.join(site_packages, "TTS", ".models.json")

        self._model_manager = ModelManager(models_json_path)

        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=FutureWarning)
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                self._model_path, self._config_path, self._model_item = \
                    self._model_manager.download_model("tts_models/en/ljspeech/tacotron2-DDC_ph")

                voc_path, voc_config_path, _ = self._model_manager. \
                    download_model("vocoder_models/en/ljspeech/univnet")
                
                self._synthesizer = Synthesizer(
                    tts_checkpoint=self._model_path,
                    tts_config_path=self._config_path,
                    vocoder_checkpoint=voc_path,
                    vocoder_config=voc_config_path
                )

    @property
    def synthesizer(self) -> Synthesizer:
        return self._synthesizer

    def synthesize(self, text: str, output_file: str = os.path.join(ROOT_DIR, ".mp", "audio.wav")) -> str:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=FutureWarning)
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                outputs = self.synthesizer.tts(text)
                self.synthesizer.save_wav(outputs, output_file)
        return output_file
