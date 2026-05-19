import re
import idna
from difflib import SequenceMatcher
from dataclasses import dataclass
from fuzzer.base import BaseFuzzer

VALID_FQDN_REGEX = re.compile(
    r"^(?=.{1,253}$)(?!-)[a-zA-Z0-9-]{1,63}(?<!-)"
    r"(\.(?!-)[a-zA-Z0-9-]{1,63}(?<!-))+$"
)

def domain_tld(domain: str):
    domain = domain.strip().lower()
    if not domain:
        raise ValueError("Enter domain")

    parts = domain.split(".")
    if len(parts) < 2:
        parts.append("com")
        
    common_multi_tlds = {
        "co.uk", "com.br", "co.jp", "com.cn", "com.tw", "net.tw",
        "ad.jp", "ne.jp", "co.th", "ac.th", "go.th", "in.th", "or.th", "mi.th", "net.th"
    }

    if len(parts) < 2:
        return "", parts[0], ""

    last_two = ".".join(parts[-2:])
    last_three = ".".join(parts[-3:]) if len(parts) >= 3 else ""

    if last_two in common_multi_tlds:
        tld = last_two
        main_domain = parts[-3] if len(parts) >= 3 else ""
        subdomain = ".".join(parts[:-3]) if len(parts) > 3 else ""
    elif last_three in common_multi_tlds:
        tld = last_three
        main_domain = parts[-4] if len(parts) >= 4 else ""
        subdomain = ".".join(parts[:-4]) if len(parts) > 4 else ""
    else:
        tld = parts[-1]
        main_domain = parts[-2]
        subdomain = ".".join(parts[:-2]) if len(parts) > 2 else ""

    if not main_domain:
        main_domain = domain
        tld = ""

    return subdomain, main_domain, tld

@dataclass(frozen=False)
class Permutation(dict):
    def __init__(self, fuzzer="", domain=""):
        super().__init__()
        self["fuzzer"] = fuzzer
        self["domain"] = domain
    def __hash__(self):
        return hash((self["fuzzer"], self["domain"]))
    def __lt__(self, other):
        return self["domain"] < other["domain"]
    def __getattr__(self, item):
        return self[item]
    def copy(self):
        return Permutation(fuzzer=self.get("fuzzer", ""), domain=self.get("domain", ""))
    def is_registered(self):
        return False

class DomainFuzzer(BaseFuzzer):
    def __init__(self, domain, dictionary=None, tld_dictionary=None):
        self.subdomain, dom, self.tld = domain_tld(domain)
        try:
            self.encoded_domain = idna.decode(dom.encode().decode())
        except Exception:
            self.encoded_domain = dom
            
        super().__init__(self.encoded_domain, dictionary)
        self.tld_dictionary = list(tld_dictionary) if tld_dictionary else []
        self.domains = set()

    def _homoglyph(self):
        return super()._homoglyph(tld=self.tld)

    def _subdomain(self):
        for i in range(1, len(self.target_word) - 1):
            if self.target_word[i] not in ['-', '.'] and self.target_word[i - 1] not in ['-', '.']:
                yield self.target_word[:i] + '.' + self.target_word[i:]

    def _tld_gen(self):
        temp_tlds = list(self.tld_dictionary)
        if self.tld in temp_tlds:
            temp_tlds.remove(self.tld)
        return set(temp_tlds)

    def generate(self, fuzzers=None):
        if fuzzers is None:
            fuzzers = []

        self.domains = set()

        if not fuzzers or '*original' in fuzzers:
            self.domains.add(
                Permutation(
                    fuzzer='*original',
                    domain='.'.join(filter(None, [self.subdomain, self.target_word, self.tld]))
                )
            )
            # Compose with .com if original TLD is not 'com'
            if self.tld and self.tld.lower() != 'com':
                self.domains.add(
                    Permutation(
                        fuzzer='*original',
                        domain='.'.join(filter(None, [self.subdomain, self.target_word, 'com']))
                    )
                )

        for f_name in fuzzers or [
            'addition', 'bitsquatting', 'cyrillic', 'homoglyph', 'hyphenation',
            'insertion', 'omission', 'plural', 'repetition', 'replacement',
            'subdomain', 'transposition', 'vowel-swap', 'dictionary'
        ]:
            try:
                f = getattr(self, '_' + f_name.replace('-', '_'))
            except AttributeError:
                pass
            else:
                # 1. generate fuzzed words จาก main_domain (ใช้ set เพื่อป้องกันคำซ้ำลดภาระการทำงาน)
                fuzzed_words = set(f())
                
                for res_word in fuzzed_words:
                    # 2. compose domain ด้วย tld เดิม
                    self.domains.add(
                        Permutation(
                            fuzzer=f_name,
                            domain='.'.join(filter(None, [self.subdomain, res_word, self.tld]))
                        )
                    )
                    # 3. ถ้า tld ไม่ใช่ com -> compose .com เพิ่ม
                    if self.tld and self.tld.lower() != 'com':
                        self.domains.add(
                            Permutation(
                                fuzzer=f_name,
                                domain='.'.join(filter(None, [self.subdomain, res_word, 'com']))
                            )
                        )

        if not fuzzers or 'tld-swap' in fuzzers:
            for tld in self._tld_gen():
                self.domains.add(
                    Permutation(
                        fuzzer='tld-swap',
                        domain='.'.join(filter(None, [self.subdomain, self.target_word, tld]))
                    )
                )

        if not fuzzers or 'various' in fuzzers:
            if '.' in self.tld:
                self.domains.add(Permutation(
                    fuzzer='various',
                    domain='.'.join(filter(None, [self.subdomain, self.target_word, self.tld.split('.')[-1]]))
                ))
                self.domains.add(Permutation(
                    fuzzer='various',
                    domain='.'.join(filter(None, [self.subdomain, self.target_word + self.tld]))
                ))

            if '.' not in self.tld:
                self.domains.add(Permutation(
                    fuzzer='various',
                    domain='.'.join(filter(None, [self.subdomain, self.target_word + self.tld, self.tld]))
                ))

            if self.tld != 'com' and '.' not in self.tld:
                self.domains.add(Permutation(
                    fuzzer='various',
                    domain='.'.join(filter(None, [self.subdomain, self.target_word + '-' + self.tld, 'com']))
                ))
                self.domains.add(Permutation(
                    fuzzer='various',
                    domain='.'.join(filter(None, [self.subdomain, self.target_word + self.tld, 'com']))
                ))

            if self.subdomain:
                self.domains.add(Permutation(
                    fuzzer='various',
                    domain='.'.join([self.subdomain + self.target_word, self.tld])
                ))
                self.domains.add(Permutation(
                    fuzzer='various',
                    domain='.'.join([self.subdomain.replace('.', '') + self.target_word, self.tld])
                ))
                self.domains.add(Permutation(
                    fuzzer='various',
                    domain='.'.join([self.subdomain + '-' + self.target_word, self.tld])
                ))
                self.domains.add(Permutation(
                    fuzzer='various',
                    domain='.'.join([self.subdomain.replace('.', '-') + '-' + self.target_word, self.tld])
                ))

        for domain in self.domains.copy():
            try:
                check_domain = idna.encode(domain.get('domain', '')).decode()
            except Exception:
                check_domain = domain.get('domain', '')

            if not VALID_FQDN_REGEX.match(check_domain):
                self.domains.discard(domain)

    def calc_similarity_score(self, test_domain: str) -> float:
        test_sub, test_main, test_tld = domain_tld(test_domain)
        
        main_sim = SequenceMatcher(None, self.target_word, test_main).ratio()
        tld_sim = 1.0 if self.tld == test_tld else 0.0
        sub_sim = 1.0 if self.subdomain == test_sub else 0.0
        
        return (main_sim * 0.80) + (tld_sim * 0.15) + (sub_sim * 0.05)

    def permutations(self, registered=False, unregistered=False, dns_all=False, unicode=False):
        if registered and not unregistered:
            domains = [x.copy() for x in self.domains if x.is_registered()]
        elif unregistered and not registered:
            domains = [x.copy() for x in self.domains if not x.is_registered()]
        else:
            domains = [x.copy() for x in self.domains]

        if not dns_all:
            def _cutdns(x):
                if x.is_registered():
                    for k in ('dns_ns', 'dns_a', 'dns_aaaa', 'dns_mx'):
                        if k in x:
                            x[k] = x[k][:1]
                return x
            domains = map(_cutdns, domains)

        if unicode:
            def _punydecode(x):
                x['domain'] = idna.decode(x['domain'])
                return x
            domains = map(_punydecode, domains)

        domains_list = list(domains)
        for x in domains_list:
            x['similarity_score'] = self.calc_similarity_score(x['domain'])

        return sorted(domains_list, key=lambda x: (-x.get('similarity_score', 0), x["domain"]))
        
    def generate_and_return(self, fuzzers):
        self.generate(fuzzers)
        return self.permutations()
