import os
import json
import re
import sys
from collections.abc import Mapping
from datetime import date, datetime

import yaml
from _project_paths import find_repo_root

# Ensure UTF-8 output for Windows compatibility
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


CATEGORY_RULES = [
    {
        "name": "security",
        "keywords": [
            "security", "auth", "authentication", "authorization", "oauth", "jwt",
            "cryptography", "encryption", "vulnerability", "threat", "pentest",
            "xss", "sqli", "gdpr", "pci", "compliance",
        ],
    },
    {
        "name": "testing",
        "keywords": [
            "test", "testing", "tdd", "qa", "e2e", "playwright", "cypress",
            "pytest", "jest", "benchmark", "evaluation", "end to end",
        ],
        "strong_keywords": ["playwright", "cypress", "pytest", "jest", "e2e", "end to end"],
    },
    {
        "name": "automation",
        "keywords": [
            "automation", "workflow", "trigger", "integration", "slack",
            "airtable", "calendar", "gmail", "google", "hubspot", "notion",
            "zendesk", "stripe", "shopify", "sendgrid", "clickup", "n8n",
            "zapier", "make", "zoom",
        ],
    },
    {
        "name": "devops",
        "keywords": [
            "docker", "kubernetes", "k8s", "helm", "terraform", "deploy",
            "deployment", "cicd", "gitops", "observability", "monitoring",
            "grafana", "prometheus", "incident", "sre", "tracing",
        ],
    },
    {
        "name": "cloud",
        "keywords": [
            "aws", "azure", "gcp", "cloud", "serverless", "lambda", "storage",
            "functions", "cdn", "azure", "azd",
        ],
    },
    {
        "name": "database",
        "keywords": [
            "database", "sql", "postgres", "postgresql", "mysql", "mongodb",
            "redis", "orm", "schema", "migration", "query", "prisma",
        ],
    },
    {
        "name": "ai-ml",
        "keywords": [
            "ai", "ml", "llm", "agent", "agents", "gpt", "embedding",
            "vector", "rag", "prompt", "model", "training", "inference",
            "pytorch", "tensorflow", "hugging", "openai",
        ],
    },
    {
        "name": "mobile",
        "keywords": [
            "mobile", "android", "ios", "swift", "swiftui", "kotlin",
            "flutter", "expo", "react native", "app store", "play store",
            "jetpack compose",
        ],
    },
    {
        "name": "game-development",
        "keywords": [
            "game", "unity", "unreal", "godot", "threejs", "3d", "2d",
            "shader", "rendering", "webgl", "physics",
        ],
    },
    {
        "name": "web-development",
        "keywords": [
            "web", "frontend", "react", "nextjs", "vue", "angular", "svelte",
            "tailwind", "css", "html", "browser", "extension", "component",
            "ui", "ux", "javascript", "typescript",
        ],
    },
    {
        "name": "backend",
        "keywords": [
            "backend", "api", "fastapi", "django", "flask", "express",
            "node", "server", "middleware", "graphql", "rest",
        ],
    },
    {
        "name": "data-science",
        "keywords": [
            "data", "analytics", "pandas", "numpy", "statistics",
            "matplotlib", "plotly", "seaborn", "scipy", "notebook",
        ],
    },
    {
        "name": "content",
        "keywords": [
            "content", "copy", "copywriting", "writing", "documentation",
            "transcription", "transcribe", "seo", "blog", "markdown",
        ],
    },
    {
        "name": "business",
        "keywords": [
            "business", "product", "market", "sales", "finance", "startup",
            "legal", "customer", "competitive", "pricing", "kpi",
        ],
    },
    {
        "name": "architecture",
        "keywords": [
            "architecture", "adr", "microservices", "ddd", "domain",
            "cqrs", "saga", "patterns",
        ],
    },
]

FAMILY_CATEGORY_RULES = [
    ("azure-", "cloud"),
    ("aws-", "cloud"),
    ("gcp-", "cloud"),
    ("apify-", "automation"),
    ("google-", "automation"),
    ("n8n-", "automation"),
    ("makepad-", "development"),
    ("robius-", "development"),
    ("avalonia-", "development"),
    ("hig-", "development"),
    ("fp-", "development"),
    ("fp-ts-", "development"),
    ("threejs-", "web-development"),
    ("react-", "web-development"),
    ("vue-", "web-development"),
    ("angular-", "web-development"),
    ("browser-", "web-development"),
    ("expo-", "mobile"),
    ("swiftui-", "mobile"),
    ("android-", "mobile"),
    ("ios-", "mobile"),
    ("hugging-face-", "ai-ml"),
    ("agent-", "ai-ml"),
    ("agents-", "ai-ml"),
    ("ai-", "ai-ml"),
    ("claude-", "ai-ml"),
    ("context-", "ai-ml"),
    ("fal-", "ai-ml"),
    ("yann-", "ai-ml"),
    ("llm-", "ai-ml"),
    ("rag-", "ai-ml"),
    ("embedding-", "ai-ml"),
    ("odoo-", "business"),
    ("product-", "business"),
    ("data-", "data-science"),
    ("wiki-", "content"),
    ("documentation-", "content"),
    ("copy", "content"),
    ("audio-", "content"),
    ("video-", "content"),
    ("api-", "backend"),
    ("django-", "backend"),
    ("fastapi-", "backend"),
    ("backend-", "backend"),
    ("python-", "development"),
    ("bash-", "development"),
    ("code-", "development"),
    ("codebase-", "development"),
    ("error-", "development"),
    ("framework-", "development"),
    ("debugging-", "development"),
    ("javascript-", "development"),
    ("go-", "development"),
    ("performance-", "development"),
    ("dbos-", "development"),
    ("conductor-", "workflow"),
    ("workflow-", "workflow"),
    ("create-", "workflow"),
    ("git-", "workflow"),
    ("github-", "workflow"),
    ("gitlab-", "workflow"),
    ("skill-", "meta"),
    ("cc-skill-", "meta"),
    ("tdd-", "testing"),
    ("test-", "testing"),
    ("security-", "security"),
    ("database-", "database"),
    ("c4-", "architecture"),
    ("deployment-", "devops"),
    ("incident-", "devops"),
    ("terraform-", "devops"),
]


def tokenize(text):
    return re.findall(r"[a-z0-9]+", text.lower())


def infer_category(skill_id, skill_name, description):
    for prefix, category in FAMILY_CATEGORY_RULES:
        if skill_id.startswith(prefix):
            return category

    normalized_name = skill_name if isinstance(skill_name, str) else ""
    normalized_description = description if isinstance(description, str) else ""
    combined_text = f"{skill_id} {normalized_name} {normalized_description}".lower()
    token_set = set(tokenize(combined_text))
    scores = {}

    for rule in CATEGORY_RULES:
        score = 0
        strong_keywords = {keyword.lower() for keyword in rule.get("strong_keywords", [])}
        for keyword in rule["keywords"]:
            keyword_lower = keyword.lower()
            if " " in keyword_lower:
                if keyword_lower in combined_text:
                    score += 4 if keyword_lower in strong_keywords else 3
                continue

            if keyword_lower in token_set:
                score += 3 if keyword_lower in strong_keywords else 2
            elif keyword_lower in combined_text:
                score += 1

        if score > 0:
            scores[rule["name"]] = score

    if not scores:
        return None

    ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    best_category, best_score = ranked[0]
    second_score = ranked[1][1] if len(ranked) > 1 else 0

    if best_score < 4:
        return None

    if best_score < 8 and (best_score - second_score) < 2:
        return None

    return best_category

def normalize_yaml_value(value):
    if isinstance(value, Mapping):
        return {key: normalize_yaml_value(val) for key, val in value.items()}
    if isinstance(value, list):
        return [normalize_yaml_value(item) for item in value]
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value

def parse_frontmatter(content):
    """
    Parses YAML frontmatter, sanitizing unquoted values containing @.
    Handles single values and comma-separated lists by quoting the entire line.
    """
    fm_match = re.search(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if not fm_match:
        return {}
    
    yaml_text = fm_match.group(1)
    
    # Process line by line to handle values containing @ and commas
    sanitized_lines = []
    for line in yaml_text.splitlines():
        # Match "key: value" (handles keys with dashes like 'package-name')
        match = re.match(r'^(\s*[\w-]+):\s*(.*)$', line)
        if match:
            key, val = match.groups()
            val_s = val.strip()
            # If value contains @ and isn't already quoted, wrap the whole string in double quotes
            if '@' in val_s and not (val_s.startswith('"') or val_s.startswith("'")):
                # Escape any existing double quotes within the value string
                safe_val = val_s.replace('"', '\\"')
                line = f'{key}: "{safe_val}"'
        sanitized_lines.append(line)
    
    sanitized_yaml = '\n'.join(sanitized_lines)
    
    try:
        parsed = yaml.safe_load(sanitized_yaml) or {}
        parsed = normalize_yaml_value(parsed)
        if not isinstance(parsed, Mapping):
            print("⚠️ YAML frontmatter must be a mapping/object")
            return {}
        return dict(parsed)
    except yaml.YAMLError as e:
        print(f"⚠️ YAML parsing error: {e}")
        return {}

def generate_index(skills_dir, output_file):
    print(f"🏗️ Generating index from: {skills_dir}")
    skills = []

    for root, dirs, files in os.walk(skills_dir):
        # Skip .disabled or hidden directories
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        
        if "SKILL.md" in files:
            skill_path = os.path.join(root, "SKILL.md")
            if os.path.islink(skill_path):
                print(f"⚠️ Skipping symlinked SKILL.md: {skill_path}")
                continue
            dir_name = os.path.basename(root)
            parent_dir = os.path.basename(os.path.dirname(root))
            
            # Default values
            rel_path = os.path.relpath(root, os.path.dirname(skills_dir))
            # Force forward slashes for cross-platform JSON compatibility
            skill_info = {
                "id": dir_name,
                "path": rel_path.replace(os.sep, '/'),
                "category": parent_dir if parent_dir != "skills" else None,  # Will be overridden by frontmatter if present
                "name": dir_name.replace("-", " ").title(),
                "description": "",
                "risk": "unknown",
                "source": "unknown",
                "date_added": None
            }
            
            try:
                with open(skill_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception as e:
                print(f"⚠️ Error reading {skill_path}: {e}")
                continue

            # Parse Metadata
            metadata = parse_frontmatter(content)
            
            # Merge Metadata (frontmatter takes priority)
            if "name" in metadata: skill_info["name"] = metadata["name"]
            if "description" in metadata: skill_info["description"] = metadata["description"]
            if "risk" in metadata: skill_info["risk"] = metadata["risk"]
            if "source" in metadata: skill_info["source"] = metadata["source"]
            if "date_added" in metadata: skill_info["date_added"] = metadata["date_added"]
            
            # Category: prefer frontmatter, then folder structure, then conservative inference
            if "category" in metadata:
                skill_info["category"] = metadata["category"]
            elif skill_info["category"] is None:
                inferred_category = infer_category(
                    skill_info["id"],
                    skill_info["name"],
                    skill_info["description"],
                )
                skill_info["category"] = inferred_category or "uncategorized"
            
            # Fallback for description if missing in frontmatter (legacy support)
            if not skill_info["description"]:
                body = content
                fm_match = re.search(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
                if fm_match:
                    body = content[fm_match.end():].strip()
                
                # Simple extraction of first non-header paragraph
                lines = body.split('\n')
                desc_lines = []
                for line in lines:
                    if line.startswith('#') or not line.strip():
                        if desc_lines: break
                        continue
                    desc_lines.append(line.strip())
                
                if desc_lines:
                    skill_info["description"] = " ".join(desc_lines)[:250].strip()

            skills.append(skill_info)

    # Sort validation: by name
    skills.sort(key=lambda x: (x["name"].lower(), x["id"].lower()))

    with open(output_file, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(skills, f, indent=2)
    
    print(f"✅ Generated rich index with {len(skills)} skills at: {output_file}")
    return skills

if __name__ == "__main__":
    base_dir = str(find_repo_root(__file__))
    skills_path = os.path.join(base_dir, "skills")
    output_path = os.path.join(base_dir, "skills_index.json")
    generate_index(skills_path, output_path)
