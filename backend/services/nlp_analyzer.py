import re
from radon.complexity import cc_visit
from radon.metrics import mi_visit, h_visit
from radon.raw import analyze
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from collections import Counter

# Download required NLTK data (only once)
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords', quiet=True)
try:
    nltk.data.find('taggers/averaged_perceptron_tagger')
except LookupError:
    nltk.download('averaged_perceptron_tagger', quiet=True)

def analyze_code_file(filename, content, fast_mode=False):
    """
    Analyze a single code file using NLP and static analysis techniques.
    Returns a dictionary of metrics and insights.
    
    Args:
        filename: Name of the file
        content: File content
        fast_mode: If True, skip expensive NLTK operations for faster analysis
    """
    results = {
        'filename': filename,
        'metrics': {},
        'smells': [],
        'naming': {},
        'documentation': {}
    }
    
    # Determine file type
    file_ext = filename.split('.')[-1] if '.' in filename else ''
    
    # Only analyze code files
    code_extensions = ['py', 'js', 'ts', 'jsx', 'tsx', 'go', 'java', 'rs', 'cpp', 'c', 'cs']
    if file_ext not in code_extensions:
        return results
    
    try:
        # Basic metrics
        lines = content.split('\n')
        results['metrics']['total_lines'] = len(lines)
        results['metrics']['non_empty_lines'] = len([l for l in lines if l.strip()])
        
        # Comment detection
        comment_lines = detect_comments(content, file_ext)
        results['metrics']['comment_lines'] = comment_lines
        results['metrics']['comment_ratio'] = round(comment_lines / max(len(lines), 1), 2)
        
        # Python-specific analysis using radon
        if file_ext == 'py':
            try:
                # Cyclomatic complexity
                complexity_blocks = cc_visit(content)
                if complexity_blocks:
                    avg_complexity = sum(block.complexity for block in complexity_blocks) / len(complexity_blocks)
                    max_complexity = max(block.complexity for block in complexity_blocks)
                    results['metrics']['avg_complexity'] = round(avg_complexity, 2)
                    results['metrics']['max_complexity'] = max_complexity
                    
                    # Flag high complexity
                    for block in complexity_blocks:
                        if block.complexity > 10:
                            results['smells'].append(f"High complexity in {block.name}: {block.complexity}")
                
                # Maintainability index
                mi_score = mi_visit(content, True)
                if mi_score:
                    results['metrics']['maintainability_index'] = round(mi_score, 2)
                
                # Halstead metrics
                h_metrics = h_visit(content)
                if h_metrics:
                    results['metrics']['halstead_difficulty'] = round(h_metrics.total.difficulty, 2)
                    results['metrics']['halstead_effort'] = round(h_metrics.total.effort, 2)
            except:
                pass
        
        # Code smell detection (language-agnostic)
        detect_code_smells(content, file_ext, results)
        
        # Naming convention analysis
        analyze_naming_conventions(content, file_ext, results)
        
        # Documentation quality
        assess_documentation(content, file_ext, results)
        
        # NLTK-based semantic analysis (skip in fast mode)
        if not fast_mode:
            semantic_analysis(content, file_ext, results)
        else:
            # Provide minimal semantic data for fast mode
            results['semantic'] = {
                'vocabulary_richness': 0.5,  # Default value
                'comment_meaningfulness': 0.5  # Default value
            }
        
    except Exception as e:
        results['error'] = str(e)
    
    return results

def detect_comments(content, file_ext):
    """Count comment lines based on file type."""
    comment_count = 0
    lines = content.split('\n')
    
    # Comment patterns by language
    single_line_patterns = {
        'py': r'^\s*#',
        'js': r'^\s*//',
        'ts': r'^\s*//',
        'jsx': r'^\s*//',
        'tsx': r'^\s*//',
        'go': r'^\s*//',
        'java': r'^\s*//',
        'rs': r'^\s*//',
        'cpp': r'^\s*//',
        'c': r'^\s*//',
        'cs': r'^\s*//'
    }
    
    pattern = single_line_patterns.get(file_ext)
    if pattern:
        for line in lines:
            if re.match(pattern, line):
                comment_count += 1
    
    return comment_count

def detect_code_smells(content, file_ext, results):
    """Detect common code smells."""
    lines = content.split('\n')
    
    # Long functions (>50 lines)
    function_patterns = {
        'py': r'^\s*def\s+(\w+)',
        'js': r'^\s*function\s+(\w+)|^\s*const\s+(\w+)\s*=\s*\(',
        'ts': r'^\s*function\s+(\w+)|^\s*const\s+(\w+)\s*=\s*\(',
        'go': r'^\s*func\s+(\w+)',
        'java': r'^\s*(public|private|protected)?\s*\w+\s+(\w+)\s*\(',
    }
    
    pattern = function_patterns.get(file_ext)
    if pattern:
        current_function = None
        function_start = 0
        
        for i, line in enumerate(lines):
            match = re.search(pattern, line)
            if match:
                if current_function and (i - function_start) > 50:
                    results['smells'].append(f"Long function '{current_function}': {i - function_start} lines")
                current_function = match.group(1) or match.group(2)
                function_start = i
    
    # Deep nesting (>4 levels)
    for i, line in enumerate(lines):
        indent_level = len(line) - len(line.lstrip())
        if file_ext == 'py':
            indent_level = indent_level // 4
        else:
            indent_level = line.count('{') - line.count('}')
        
        if indent_level > 4:
            results['smells'].append(f"Deep nesting at line {i+1}: {indent_level} levels")
            break  # Only report first occurrence

def analyze_naming_conventions(content, file_ext, results):
    """Analyze naming conventions used in the code."""
    # Extract identifiers
    identifier_pattern = r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b'
    identifiers = re.findall(identifier_pattern, content)
    
    if not identifiers:
        return
    
    # Count naming styles
    snake_case = sum(1 for i in identifiers if '_' in i and i.islower())
    camel_case = sum(1 for i in identifiers if i[0].islower() and any(c.isupper() for c in i))
    pascal_case = sum(1 for i in identifiers if i[0].isupper() and any(c.isupper() for c in i[1:]))
    
    total = len(identifiers)
    results['naming']['snake_case_ratio'] = round(snake_case / total, 2)
    results['naming']['camel_case_ratio'] = round(camel_case / total, 2)
    results['naming']['pascal_case_ratio'] = round(pascal_case / total, 2)
    
    # Determine dominant convention
    dominant = max([
        ('snake_case', snake_case),
        ('camelCase', camel_case),
        ('PascalCase', pascal_case)
    ], key=lambda x: x[1])
    
    results['naming']['dominant_convention'] = dominant[0]
    results['naming']['consistency_score'] = round(dominant[1] / total, 2)

def assess_documentation(content, file_ext, results):
    """Assess documentation quality."""
    lines = content.split('\n')
    
    # Docstring detection (Python)
    if file_ext == 'py':
        docstring_pattern = r'^\s*""".*?"""'
        docstrings = len(re.findall(docstring_pattern, content, re.DOTALL))
        results['documentation']['docstrings'] = docstrings
    
    # JSDoc detection (JS/TS)
    if file_ext in ['js', 'ts', 'jsx', 'tsx']:
        jsdoc_pattern = r'/\*\*.*?\*/'
        jsdocs = len(re.findall(jsdoc_pattern, content, re.DOTALL))
        results['documentation']['jsdocs'] = jsdocs
    
    # TODO/FIXME detection
    todo_count = len(re.findall(r'TODO|FIXME|XXX', content, re.IGNORECASE))
    results['documentation']['todos'] = todo_count

def generate_nlp_summary(file_analyses):
    """
    Generate a summary of NLP analysis across all files.
    """
    if not file_analyses:
        return "No files analyzed."
    
    summary = []
    
    # Aggregate metrics
    total_files = len(file_analyses)
    total_lines = sum(f['metrics'].get('total_lines', 0) for f in file_analyses)
    avg_comment_ratio = sum(f['metrics'].get('comment_ratio', 0) for f in file_analyses) / total_files
    
    summary.append(f"Analyzed {total_files} files with {total_lines} total lines of code.")
    summary.append(f"Average comment ratio: {round(avg_comment_ratio * 100, 1)}%")
    
    # Complexity (Python files)
    py_files = [f for f in file_analyses if 'avg_complexity' in f['metrics']]
    if py_files:
        avg_complexity = sum(f['metrics']['avg_complexity'] for f in py_files) / len(py_files)
        summary.append(f"Average cyclomatic complexity: {round(avg_complexity, 2)}")
    
    # Code smells
    all_smells = [smell for f in file_analyses for smell in f.get('smells', [])]
    if all_smells:
        summary.append(f"\nDetected {len(all_smells)} code smells:")
        for smell in all_smells[:5]:  # Top 5
            summary.append(f"  - {smell}")
    
    # Naming conventions
    naming_conventions = [f['naming'].get('dominant_convention') for f in file_analyses if f.get('naming')]
    if naming_conventions:
        from collections import Counter
        most_common = Counter(naming_conventions).most_common(1)[0]
        summary.append(f"\nDominant naming convention: {most_common[0]}")
    
    return "\n".join(summary)

def semantic_analysis(content, file_ext, results):
    """Use NLTK for semantic analysis of identifiers and comments."""
    try:
        # Extract identifiers (variable/function names)
        identifier_pattern = r'\b([a-zA-Z_][a-zA-Z0-9_]{2,})\b'
        identifiers = re.findall(identifier_pattern, content)
        
        if identifiers:
            # Tokenize identifier names (split camelCase and snake_case)
            identifier_words = []
            for identifier in identifiers:
                # Split on underscores
                parts = identifier.split('_')
                for part in parts:
                    # Split camelCase
                    words = re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?=[A-Z][a-z]|\b)', part)
                    identifier_words.extend([w.lower() for w in words if len(w) > 1])
            
            if identifier_words:
                # Remove common programming keywords
                stop_words = set(stopwords.words('english'))
                programming_keywords = {'def', 'class', 'return', 'import', 'from', 'if', 'else', 'for', 'while', 'try', 'except'}
                filtered_words = [w for w in identifier_words if w not in stop_words and w not in programming_keywords]
                
                # Analyze identifier vocabulary
                word_freq = Counter(filtered_words)
                unique_words = len(word_freq)
                total_words = len(filtered_words)
                
                results['semantic'] = {
                    'unique_identifier_words': unique_words,
                    'total_identifier_words': total_words,
                    'vocabulary_richness': round(unique_words / max(total_words, 1), 2),
                    'most_common_terms': [word for word, _ in word_freq.most_common(5)]
                }
        
        # Analyze comments for meaningfulness
        comments = extract_comments_text(content, file_ext)
        if comments:
            # Tokenize comments
            comment_tokens = []
            for comment in comments:
                tokens = word_tokenize(comment.lower())
                comment_tokens.extend([t for t in tokens if t.isalpha()])
            
            if comment_tokens:
                # POS tagging to find meaningful content (nouns, verbs, adjectives)
                pos_tags = nltk.pos_tag(comment_tokens)
                meaningful_tags = ['NN', 'NNS', 'VB', 'VBD', 'VBG', 'VBN', 'VBP', 'VBZ', 'JJ', 'JJR', 'JJS']
                meaningful_words = [word for word, tag in pos_tags if tag in meaningful_tags]
                
                if comment_tokens:
                    results['semantic']['comment_meaningfulness'] = round(len(meaningful_words) / len(comment_tokens), 2)
                    results['semantic']['avg_comment_length'] = round(sum(len(c.split()) for c in comments) / len(comments), 1)
    
    except Exception as e:
        # NLTK errors shouldn't break the analysis
        pass

def extract_comments_text(content, file_ext):
    """Extract actual comment text (not just count)."""
    comments = []
    lines = content.split('\n')
    
    comment_patterns = {
        'py': r'^\s*#\s*(.+)',
        'js': r'^\s*//\s*(.+)',
        'ts': r'^\s*//\s*(.+)',
        'jsx': r'^\s*//\s*(.+)',
        'tsx': r'^\s*//\s*(.+)',
        'go': r'^\s*//\s*(.+)',
        'java': r'^\s*//\s*(.+)',
    }
    
    pattern = comment_patterns.get(file_ext)
    if pattern:
        for line in lines:
            match = re.match(pattern, line)
            if match:
                comments.append(match.group(1).strip())
    
    return comments
