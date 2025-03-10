from openai import OpenAI

client = OpenAI(api_key="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")

try:
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": "Hello!"}]
    )
    print("Success:", response.choices[0].message.content)
except Exception as e:
    print("Error:", e)