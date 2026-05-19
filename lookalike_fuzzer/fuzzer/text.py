from fuzzer.base import BaseFuzzer

class TextFuzzer(BaseFuzzer):
    def generate_and_return(self, fuzzers=None):
        if fuzzers is None:
            fuzzers = []

        results = set()
        if not fuzzers or '*original' in fuzzers:
            results.add(self.target_word)

        for f_name in fuzzers or [
            'addition', 'bitsquatting', 'cyrillic', 'homoglyph', 'hyphenation',
            'insertion', 'omission', 'plural', 'repetition', 'replacement',
            'transposition', 'vowel-swap', 'dictionary'
        ]:
            try:
                f = getattr(self, '_' + f_name.replace('-', '_'))
            except AttributeError:
                pass
            else:
                for res_word in f():
                    results.add(res_word)

        # ห่อ list ที่รวบรวมได้ส่งคืนเป็น List[str] ล้วนๆ ไม่ต้องติดเป็น Object Fuzzer
        return sorted(list(results))
