import re
import requests
import openai
import json

def load_api_key(file_path="config/open.key"):
    with open(file_path, 'r') as f:
        return f.read().strip()
        
def load_section_rules(path="config/rules.json"):
    with open(path, "r") as f:
        return json.load(f)

def extract_sections(raw_text):
    text = raw_text.replace('\\n', '\n')

    abstract_match = re.search(r"^(.*?)^\s*Introduction\s*$", text, re.MULTILINE | re.DOTALL | re.IGNORECASE)
    abstract = abstract_match.group(1).strip() if abstract_match else None

    section_order = ["introduction", "results", "discussion", "methods", "references"]
    section_patterns = {
        "introduction": r"^Introduction\s*$",
        "results": r"^Results\s*$",
        "discussion": r"^Discussion\s*$",
        "methods": r"^Methods\s*$",
        "references": r"^References\s*$"
    }

    extracted = {"abstract": abstract}
    section_positions = {}

    for name, pattern in section_patterns.items():
        match = re.search(pattern, text, re.MULTILINE | re.IGNORECASE)
        if match:
            section_positions[name] = match.start()

    sorted_sections = sorted(section_positions.items(), key=lambda x: x[1])

    for i, (section, start_idx) in enumerate(sorted_sections):
        end_idx = len(text) if i + 1 == len(sorted_sections) else sorted_sections[i + 1][1]
        content = text[start_idx:end_idx]
        content = re.sub(section_patterns[section], '', content, count=1, flags=re.IGNORECASE | re.MULTILINE).strip()
        extracted[section] = content

    for sec in section_order:
        if sec not in extracted:
            extracted[sec] = None

    return extracted


def edit_section(text, prompt, client):
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": text}
        ],
        temperature=0.2
    )
    return response.choices[0].message.content.strip()


def main(document_id):
    api_key = load_api_key()
    client = openai.OpenAI(api_key=api_key)
    section_rules = load_section_rules()

    url = f"https://docs.google.com/document/d/{document_id}/export?format=txt"
    response = requests.get(url)

    if response.status_code != 200:
        raise Exception(f"Failed to fetch document: HTTP {response.status_code}")

    raw_text = response.text
    parsed = extract_sections(raw_text)
    edited_sections = {}

    for section, content in parsed.items():
        if content and section in section_rules:
            print(f"Editing section: {section}")
            edited = edit_section(content, section_rules[section], client)
            edited_sections[section] = edited

    return edited_sections


if __name__ == "__main__":
    import sys
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Edit a Google Doc via GPT and save the result as JSON.")
    parser.add_argument("document_id", help="Google Docs ID (must be shared with 'Anyone with the link')")
    parser.add_argument("--output", "-o", default="gpt-edited.json", help="Output filename (default: edited.json)")
    args = parser.parse_args()

    result = main(args.document_id)

    # Save to file
    with open(args.output, "w") as f:
        json.dump(result, f, indent=2)

