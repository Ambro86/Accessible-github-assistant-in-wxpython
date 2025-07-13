"""
Utility functions per Assistente Git.
Modulo separato per funzioni di utilità e validazione.
"""

import os
import re
import logging
from typing import Optional, List, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


def sanitize_input(input_str: str, max_length: int = 1000) -> str:
    """Sanitizza l'input dell'utente per prevenire injection.
    
    Args:
        input_str: Stringa di input da sanitizzare
        max_length: Lunghezza massima consentita
        
    Returns:
        Stringa sanitizzata
    """
    if not input_str:
        return ""
        
    # Rimuovi caratteri potenzialmente pericolosi
    sanitized = re.sub(r'[;&|`$\(\)]', '', input_str)
    
    # Limita la lunghezza
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
        logger.warning(f"Input troncato a {max_length} caratteri")
        
    return sanitized.strip()


def validate_git_command(cmd_parts: List[str]) -> bool:
    """Valida che un comando Git sia sicuro da eseguire.
    
    Args:
        cmd_parts: Lista delle parti del comando
        
    Returns:
        True se il comando è sicuro, False altrimenti
    """
    if not cmd_parts or not isinstance(cmd_parts, list):
        return False
        
    # Il primo elemento deve essere 'git'
    if cmd_parts[0] != 'git':
        return False
        
    # Lista di comandi Git considerati sicuri
    safe_commands = {
        'status', 'add', 'commit', 'push', 'pull', 'fetch', 'clone',
        'branch', 'checkout', 'merge', 'log', 'diff', 'remote',
        'tag', 'reset', 'revert', 'stash', 'cherry-pick', 'rebase',
        'show', 'grep', 'ls-files', 'init', 'config'
    }
    
    if len(cmd_parts) > 1 and cmd_parts[1] not in safe_commands:
        logger.warning(f"Comando Git non sicuro rilevato: {cmd_parts[1]}")
        return False
        
    return True


def validate_repository_path(repo_path: str) -> tuple[bool, Optional[str]]:
    """Valida un percorso di repository Git.
    
    Args:
        repo_path: Percorso da validare
        
    Returns:
        Tupla (is_valid, error_message)
    """
    if not repo_path or not repo_path.strip():
        return False, "Percorso repository vuoto"
        
    path = Path(repo_path)
    
    if not path.exists():
        return False, f"Il percorso non esiste: {repo_path}"
        
    if not path.is_dir():
        return False, f"Il percorso non è una directory: {repo_path}"
        
    # Controlla se è un repository Git
    git_dir = path / ".git"
    if not git_dir.exists():
        return False, f"Directory non è un repository Git: {repo_path}"
        
    return True, None


def format_file_size(size_bytes: int) -> str:
    """Formatta una dimensione in bytes in formato leggibile.
    
    Args:
        size_bytes: Dimensione in bytes
        
    Returns:
        Stringa formattata (es. "1.5 MB")
    """
    if size_bytes == 0:
        return "0 B"
        
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    unit_index = 0
    size = float(size_bytes)
    
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
        
    return f"{size:.1f} {units[unit_index]}"


def truncate_text(text: str, max_length: int = 100) -> str:
    """Tronca un testo a una lunghezza massima.
    
    Args:
        text: Testo da troncare
        max_length: Lunghezza massima
        
    Returns:
        Testo troncato con "..." se necessario
    """
    if not text or len(text) <= max_length:
        return text
        
    return text[:max_length - 3] + "..."


def is_safe_filename(filename: str) -> bool:
    """Verifica se un nome file è sicuro.
    
    Args:
        filename: Nome del file da verificare
        
    Returns:
        True se il nome è sicuro, False altrimenti
    """
    if not filename or not filename.strip():
        return False
        
    # Caratteri non consentiti nei nomi file
    forbidden_chars = ['<', '>', ':', '"', '|', '?', '*', '\\', '/']
    
    for char in forbidden_chars:
        if char in filename:
            return False
            
    # Nomi riservati Windows
    reserved_names = [
        'CON', 'PRN', 'AUX', 'NUL',
        'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
        'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
    ]
    
    if filename.upper() in reserved_names:
        return False
        
    return True


class PerformanceMonitor:
    """Monitor delle performance per operazioni lunghe."""
    
    def __init__(self, name: str):
        self.name = name
        self.start_time = None
        self.end_time = None
        
    def __enter__(self):
        import time
        self.start_time = time.time()
        logger.debug(f"Inizio operazione: {self.name}")
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        import time
        self.end_time = time.time()
        duration = self.end_time - self.start_time
        logger.info(f"Operazione '{self.name}' completata in {duration:.2f} secondi")
        
        if duration > 5.0:  # Operazioni che durano più di 5 secondi
            logger.warning(f"Operazione lenta rilevata: '{self.name}' ({duration:.2f}s)")