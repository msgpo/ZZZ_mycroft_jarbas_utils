from mycroft.skills.core import MycroftSkill, FallbackSkill, Message, \
    dig_for_message
from mtranslate import translate
import unicodedata
from langdetect import detect as language_detect


class AutotranslatableSkill(MycroftSkill):
    ''' Skill that auto translates speak messages '''

    def __init__(self, name=None, emitter=None):
        MycroftSkill.__init__(self, name, emitter)

    def language_detect(self, utterance):
        utterance = unicodedata.normalize('NFKD', unicode(utterance)).encode(
            'ascii',
            'ignore')
        return language_detect(utterance)

    def translate(self, text, lang=None):
        lang = lang or self.lang
        sentence = translate(unicode(text), lang)
        translated = unicodedata.normalize('NFKD', unicode(sentence)).encode(
            'ascii',
            'ignore')
        return translated

    def speak(self, utterance, expect_response=False, metadata=None):
        """
            Speak a sentence.

                   Args:
                       utterance:          sentence mycroft should speak
                       expect_response:    set to True if Mycroft should expect
                                           a response from the user and start
                                           listening for response.
                       metadata:           Extra data to be transmitted
                                           together with speech
               """
        # translate utterance for skills that generate speech at
        # runtime, or by request
        message_context = {}
        utterance_lang = self.language_detect(utterance)
        if "-" in utterance_lang:
            utterance_lang = utterance_lang.split("-")[0]
        target_lang = self.lang
        if "-" in target_lang:
            target_lang = target_lang.split("-")[0]
        if utterance_lang != target_lang:
            utterance = self.translate(utterance, target_lang)
            message_context["auto_translated"] = True
            message_context["source_lang"] = utterance_lang
            message_context["target_lang"] = target_lang

        # registers the skill as being active
        self.enclosure.register(self.name)
        data = {'utterance': utterance,
                'expect_response': expect_response,
                "metadata": metadata}
        message = dig_for_message()
        if message:
            self.emitter.emit(message.reply("speak", data, message_context))
        else:
            self.emitter.emit(Message("speak", data, message_context))


class AutotranslatableFallback(AutotranslatableSkill, FallbackSkill):
    ''' Fallback that auto translates speak messages and auto translates
    input utterances '''

    def __init__(self, name=None, emitter=None):
        FallbackSkill.__init__(self, name, emitter)
        self.input_lang = None

        def handler(message):
            return False

        self._handler = handler

    def _universal_fallback_handler(self, message):
        # auto_Translate input
        ut = message.data.get("utterance")
        if ut:
            ut_lang = self.language_detect(ut)
            if "-" in ut_lang:
                ut_lang = ut_lang.split("-")[0]
            if "-" in self.input_lang:
                self.input_lang = self.input_lang.split("-")[0]
            if self.input_lang != ut_lang:
                message.data["utterance"] = self.translate(ut,
                                                           self.input_lang)
        success = self._handler(message)
        if success:
            self.make_active()
        return success

    def register_fallback(self, handler, priority):
        """
            register a fallback with the list of fallback handlers
            and with the list of handlers registered by this instance

            modify fallback handler for input auto-translation
        """

        self._handler = handler

        if self.input_lang:
            self.instance_fallback_handlers.append(
                self._universal_fallback_handler)
            self._register_fallback(self._universal_fallback_handler,
                                    priority)
        else:
            self.instance_fallback_handlers.append(handler)
            self._register_fallback(handler, priority)