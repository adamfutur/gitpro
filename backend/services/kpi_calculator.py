import numpy as np
from datetime import datetime

def calculate_kpis(nlp_analyses, repo_data, commits=None, prs=None):
    """
    Calculate comprehensive KPIs for repository health.
    
    Args:
        nlp_analyses: List of NLP analysis results for files
        repo_data: Repository metadata (stars, forks, etc.)
        commits: Recent commits data
        prs: Recent pull requests data
    
    Returns:
        Dictionary of KPIs organized by category
    """
    
    if not nlp_analyses:
        return _empty_kpis()
    
    kpis = {
        'quality': _calculate_quality_kpis(nlp_analyses),
        'maintainability': _calculate_maintainability_kpis(nlp_analyses),
        'productivity': _calculate_productivity_kpis(commits, prs),
        'security': _calculate_security_kpis(nlp_analyses),
        'summary': {}
    }
    
    # Overall health score (weighted average)
    kpis['summary']['overall_health_score'] = _calculate_overall_score(kpis)
    kpis['summary']['grade'] = _score_to_grade(kpis['summary']['overall_health_score'])
    kpis['summary']['analyzed_files'] = len(nlp_analyses)
    kpis['summary']['timestamp'] = datetime.utcnow().isoformat()
    
    return kpis

def _calculate_quality_kpis(nlp_analyses):
    """Calculate code quality KPIs."""
    total_lines = sum(a['metrics'].get('total_lines', 0) for a in nlp_analyses)
    total_smells = sum(len(a.get('smells', [])) for a in nlp_analyses)
    
    # Average complexity (Python files only)
    complexities = [a['metrics'].get('avg_complexity', 0) for a in nlp_analyses if 'avg_complexity' in a['metrics']]
    avg_complexity = np.mean(complexities) if complexities else 0
    
    # Comment ratio
    comment_ratios = [a['metrics'].get('comment_ratio', 0) for a in nlp_analyses]
    avg_comment_ratio = np.mean(comment_ratios) if comment_ratios else 0
    
    # Code smell density (per 1000 LOC)
    smell_density = (total_smells / max(total_lines, 1)) * 1000
    
    # Quality score (0-100)
    quality_score = _calculate_quality_score(avg_complexity, avg_comment_ratio, smell_density)
    
    return {
        'quality_score': round(quality_score, 1),
        'avg_complexity': round(avg_complexity, 2),
        'code_smell_density': round(smell_density, 2),
        'documentation_coverage': round(avg_comment_ratio * 100, 1),
        'total_code_smells': total_smells,
        'total_lines_of_code': total_lines
    }

def _calculate_maintainability_kpis(nlp_analyses):
    """Calculate maintainability KPIs."""
    # Maintainability index (Python files)
    mi_scores = [a['metrics'].get('maintainability_index', 0) for a in nlp_analyses if 'maintainability_index' in a['metrics']]
    avg_mi = np.mean(mi_scores) if mi_scores else 0
    
    # Naming consistency
    naming_scores = [a['naming'].get('consistency_score', 0) for a in nlp_analyses if a.get('naming')]
    avg_naming_consistency = np.mean(naming_scores) if naming_scores else 0
    
    # Vocabulary richness (semantic analysis)
    vocab_scores = [a['semantic'].get('vocabulary_richness', 0) for a in nlp_analyses if a.get('semantic')]
    avg_vocab_richness = np.mean(vocab_scores) if vocab_scores else 0
    
    # Technical debt estimation (hours)
    # Based on code smells and complexity
    total_smells = sum(len(a.get('smells', [])) for a in nlp_analyses)
    high_complexity_files = sum(1 for a in nlp_analyses if a['metrics'].get('max_complexity', 0) > 10)
    technical_debt_hours = (total_smells * 2) + (high_complexity_files * 8)  # Rough estimate
    
    return {
        'maintainability_index': round(avg_mi, 1),
        'naming_consistency': round(avg_naming_consistency * 100, 1),
        'vocabulary_richness': round(avg_vocab_richness * 100, 1),
        'technical_debt_hours': technical_debt_hours,
        'technical_debt_days': round(technical_debt_hours / 8, 1)
    }

def _calculate_productivity_kpis(commits, prs):
    """Calculate productivity KPIs from Git activity."""
    if not commits and not prs:
        return {
            'productivity_score': 0,
            'commit_frequency': 0,
            'pr_merge_rate': 0,
            'avg_pr_size': 0,
            'active_contributors': 0
        }
    
    # Commit frequency (commits per week estimate)
    commit_count = len(commits) if commits else 0
    commit_frequency = commit_count  # Simplified (assumes recent commits)
    
    # PR metrics
    pr_count = len(prs) if prs else 0
    merged_prs = sum(1 for pr in (prs or []) if pr.get('merged_at')) if prs else 0
    pr_merge_rate = (merged_prs / max(pr_count, 1)) * 100 if pr_count > 0 else 0
    
    # Active contributors (unique commit authors)
    contributors = set()
    if commits:
        for commit in commits:
            author = commit.get('commit', {}).get('author', {}).get('name')
            if author:
                contributors.add(author)
    
    # Calculate productivity score (0-100)
    # Based on: commit activity (40%), PR merge rate (30%), team size (30%)
    commit_score = min(100, (commit_count / 10) * 100)  # 10+ commits/week = 100
    pr_score = pr_merge_rate if pr_count > 0 else 50  # Default to 50 if no PRs
    contributor_score = min(100, (len(contributors) / 5) * 100)  # 5+ contributors = 100
    
    productivity_score = (commit_score * 0.4) + (pr_score * 0.3) + (contributor_score * 0.3)
    
    return {
        'productivity_score': round(productivity_score, 1),
        'commit_frequency': commit_count,
        'pr_merge_rate': round(pr_merge_rate, 1),
        'avg_pr_size': 0,  # Would need PR file changes data
        'active_contributors': len(contributors)
    }

def _calculate_security_kpis(nlp_analyses):
    """Calculate security-related KPIs."""
    # Count security-related code smells
    security_keywords = ['password', 'secret', 'token', 'api_key', 'private_key']
    security_issues = 0
    
    for analysis in nlp_analyses:
        smells = analysis.get('smells', [])
        for smell in smells:
            if any(keyword in smell.lower() for keyword in security_keywords):
                security_issues += 1
    
    # Risk score based on various factors
    total_smells = sum(len(a.get('smells', [])) for a in nlp_analyses)
    high_complexity_count = sum(1 for a in nlp_analyses if a['metrics'].get('max_complexity', 0) > 15)
    
    risk_score = min(100, (security_issues * 10) + (high_complexity_count * 5) + (total_smells * 2))
    
    return {
        'security_issue_count': security_issues,
        'risk_score': risk_score,
        'high_complexity_files': high_complexity_count
    }

def _calculate_quality_score(avg_complexity, comment_ratio, smell_density):
    """
    Calculate overall quality score (0-100).
    Higher is better.
    """
    # Complexity score (lower is better, ideal is 1-5)
    complexity_score = max(0, 100 - (avg_complexity - 5) * 10) if avg_complexity > 5 else 100
    complexity_score = max(0, min(100, complexity_score))
    
    # Documentation score (higher is better, ideal is 15-30%)
    doc_score = min(100, comment_ratio * 300)  # 30% = 90 points
    
    # Code smell score (lower is better, ideal is < 5 per 1000 LOC)
    smell_score = max(0, 100 - smell_density * 5)
    smell_score = max(0, min(100, smell_score))
    
    # Weighted average
    quality_score = (complexity_score * 0.4) + (doc_score * 0.3) + (smell_score * 0.3)
    
    return quality_score

def _calculate_overall_score(kpis):
    """Calculate overall health score from all KPIs."""
    quality = kpis['quality']['quality_score']
    maintainability = kpis['maintainability']['maintainability_index']
    
    # Weighted average
    overall = (quality * 0.6) + (maintainability * 0.4)
    
    return round(overall, 1)

def _score_to_grade(score):
    """Convert numeric score to letter grade."""
    if score >= 90:
        return 'A'
    elif score >= 80:
        return 'B'
    elif score >= 70:
        return 'C'
    elif score >= 60:
        return 'D'
    else:
        return 'F'

def _empty_kpis():
    """Return empty KPI structure."""
    return {
        'quality': {},
        'maintainability': {},
        'productivity': {},
        'security': {},
        'summary': {
            'overall_health_score': 0,
            'grade': 'N/A',
            'analyzed_files': 0
        }
    }
