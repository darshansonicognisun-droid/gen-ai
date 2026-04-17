import tiktoken


def count_tokens(text, model="gpt-3.5-turbo"):
    encoding = tiktoken.encoding_for_model(model)
    tokens = encoding.encode(text)
    return len(tokens)


law_text = """The capital of France is Paris. 

Paris has been the capital of France since 987, when Hugh Capet, the Count of Paris, became the King of France, marking the beginning of the Capetian dynasty. The city's strategic location, situated in the northern part of the country, made it an ideal place for the capital. 

Several reasons contribute to Paris being the capital:
1. **Strategic location**: Paris is located near the center of the country's most populous and economically"""

print(f"Tokens: {count_tokens(law_text)}")
