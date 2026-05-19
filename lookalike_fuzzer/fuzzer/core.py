from fuzzer.text import TextFuzzer
from fuzzer.domain import DomainFuzzer

def generate_fuzz(input_val: str, dictionary=None, tld_dictionary=None, fuzzers=None, mode="auto"):
    if dictionary is None:
        dictionary = []
    if tld_dictionary is None:
        tld_dictionary = []
    if fuzzers is None:
        fuzzers = []

    if mode == "auto":
        mode = "domain" if "." in input_val else "text"
        
    if mode == "text":
        fuzzer = TextFuzzer(input_val, dictionary)
        return fuzzer.generate_and_return(fuzzers)
    elif mode == "domain":
        fuzzer = DomainFuzzer(input_val, dictionary, tld_dictionary)
        return fuzzer.generate_and_return(fuzzers)
    else:
        raise ValueError("Invalid mode. Use 'auto', 'text', or 'domain'.")

# Alias สำหรับ API เก่าที่เคยเรียกคำสั่งเดิม
generate_similar_domains = lambda word, dictionary=None, tld_dictionary=None, fuzzers=None: generate_fuzz(word, dictionary=dictionary, tld_dictionary=tld_dictionary, fuzzers=fuzzers, mode="domain")
generate_similar_strings = lambda word, fuzzers=None: generate_fuzz(word, mode="text", fuzzers=fuzzers)
