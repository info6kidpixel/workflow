#!/usr/bin/env python
"""
Analyseur de logs pour l'application de workflow
Ce script permet de filtrer et d'analyser les logs de l'application.
"""

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path
import json
import csv

def parse_log_line(line):
    """Parse une ligne de log et extrait les informations importantes. Retourne None si non reconnu."""
    pattern = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) - (\w+) - (\w+) - ([^-]+) - (.+) \[in ([^:]+):(\d+)\]'
    try:
        match = re.match(pattern, line)
        if match:
            timestamp, module, level, thread, message, file, line_num = match.groups()
            return {
                'timestamp': timestamp,
                'module': module,
                'level': level,
                'thread': thread.strip(),
                'message': message.strip(),
                'file': file,
                'line_num': int(line_num)
            }
    except Exception as e:
        print(f"Erreur lors du parsing de la ligne: {e}\nLigne: {line.strip()}")
    return None

def filter_logs(log_file, output_format='text', level=None, module=None, thread=None, message_pattern=None, start_time=None, end_time=None, output_file=None, show_unparsed=False):
    """Filtre les logs selon les critères spécifiés. Affiche les lignes non reconnues si show_unparsed."""
    log_path = Path(log_file)
    if not log_path.exists():
        print(f"Erreur: Le fichier de log '{log_file}' n'existe pas.")
        return

    filtered_logs = []
    unparsed_lines = []
    with open(log_path, 'r', encoding='utf-8') as f:
        for line in f:
            log_entry = parse_log_line(line)
            if not log_entry:
                unparsed_lines.append(line.rstrip())
                continue
            try:
                # Appliquer les filtres
                if level and log_entry['level'] != level:
                    continue
                if module and log_entry['module'] != module:
                    continue
                if thread and thread not in log_entry['thread']:
                    continue
                if message_pattern and not re.search(message_pattern, log_entry['message']):
                    continue
                if start_time:
                    try:
                        log_time = datetime.strptime(log_entry['timestamp'], '%Y-%m-%d %H:%M:%S,%f')
                    except Exception as e:
                        print(f"Erreur parsing date: {e} (ligne: {log_entry['timestamp']})")
                        continue
                    if log_time < start_time:
                        continue
                if end_time:
                    try:
                        log_time = datetime.strptime(log_entry['timestamp'], '%Y-%m-%d %H:%M:%S,%f')
                    except Exception as e:
                        print(f"Erreur parsing date: {e} (ligne: {log_entry['timestamp']})")
                        continue
                    if log_time > end_time:
                        continue
            except Exception as e:
                print(f"Erreur lors du filtrage: {e}\nEntrée: {log_entry}")
                continue
            filtered_logs.append(log_entry)

    # Sortie des résultats
    if output_format == 'text':
        output_text_format(filtered_logs, output_file)
    elif output_format == 'json':
        output_json_format(filtered_logs, output_file)
    elif output_format == 'csv':
        output_csv_format(filtered_logs, output_file)
    else:
        print(f"Format de sortie '{output_format}' non pris en charge.")

    print(f"\nLignes reconnues: {len(filtered_logs)} | Lignes ignorées/non reconnues: {len(unparsed_lines)}")
    if show_unparsed and unparsed_lines:
        print("\n--- Lignes non reconnues ---")
        for l in unparsed_lines:
            print(l)

def output_text_format(logs, output_file=None):
    """Affiche les logs au format texte."""
    output = sys.stdout if not output_file else open(output_file, 'w', encoding='utf-8')
    for log in logs:
        output.write(f"{log['timestamp']} - {log['level']} - {log['thread']} - {log['message']}\n")
    if output_file:
        output.close()

def output_json_format(logs, output_file=None):
    """Affiche les logs au format JSON."""
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(logs, f, indent=2)
    else:
        print(json.dumps(logs, indent=2))

def output_csv_format(logs, output_file=None):
    """Affiche les logs au format CSV."""
    output = sys.stdout if not output_file else open(output_file, 'w', encoding='utf-8', newline='')
    writer = csv.DictWriter(output, fieldnames=['timestamp', 'module', 'level', 'thread', 'message', 'file', 'line_num'])
    writer.writeheader()
    for log in logs:
        writer.writerow(log)
    if output_file:
        output.close()

def analyze_logs(log_file):
    """Analyse les logs et génère des statistiques."""
    log_path = Path(log_file)
    if not log_path.exists():
        print(f"Erreur: Le fichier de log '{log_file}' n'existe pas.")
        return

    stats = {
        'total_entries': 0,
        'by_level': {},
        'by_module': {},
        'by_thread': {},
        'errors': [],
        'warnings': [],
        'client_errors': [],
        'gpu_operations': [],
        'sequence_operations': []
    }

    with open(log_path, 'r', encoding='utf-8') as f:
        for line in f:
            log_entry = parse_log_line(line)
            if not log_entry:
                continue

            stats['total_entries'] += 1
            
            # Statistiques par niveau
            level = log_entry['level']
            stats['by_level'][level] = stats['by_level'].get(level, 0) + 1
            
            # Statistiques par module
            module = log_entry['module']
            stats['by_module'][module] = stats['by_module'].get(module, 0) + 1
            
            # Statistiques par thread
            thread = log_entry['thread']
            stats['by_thread'][thread] = stats['by_thread'].get(thread, 0) + 1
            
            # Collecter les erreurs et avertissements
            if level == 'ERROR':
                stats['errors'].append(log_entry)
            elif level == 'WARNING':
                stats['warnings'].append(log_entry)
            
            # Collecter les erreurs client
            if 'CLIENT ERROR' in log_entry['message']:
                stats['client_errors'].append(log_entry)
            
            # Collecter les opérations GPU
            if 'GPU' in log_entry['message']:
                stats['gpu_operations'].append(log_entry)
            
            # Collecter les opérations de séquence
            if 'SEQUENCE' in log_entry['message']:
                stats['sequence_operations'].append(log_entry)

    # Afficher les statistiques
    print(f"=== Analyse des logs ===")
    print(f"Total des entrées: {stats['total_entries']}")
    
    print("\n=== Répartition par niveau ===")
    for level, count in stats['by_level'].items():
        print(f"{level}: {count} ({count/stats['total_entries']*100:.1f}%)")
    
    print("\n=== Répartition par module ===")
    for module, count in stats['by_module'].items():
        print(f"{module}: {count} ({count/stats['total_entries']*100:.1f}%)")
    
    print("\n=== Répartition par thread ===")
    for thread, count in sorted(stats['by_thread'].items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"{thread}: {count} ({count/stats['total_entries']*100:.1f}%)")
    
    print(f"\n=== Erreurs ({len(stats['errors'])}) ===")
    for error in stats['errors'][:5]:
        print(f"{error['timestamp']} - {error['message']}")
    if len(stats['errors']) > 5:
        print(f"... et {len(stats['errors'])-5} autres erreurs")
    
    print(f"\n=== Avertissements ({len(stats['warnings'])}) ===")
    for warning in stats['warnings'][:5]:
        print(f"{warning['timestamp']} - {warning['message']}")
    if len(stats['warnings']) > 5:
        print(f"... et {len(stats['warnings'])-5} autres avertissements")
    
    print(f"\n=== Erreurs client ({len(stats['client_errors'])}) ===")
    for error in stats['client_errors'][:5]:
        print(f"{error['timestamp']} - {error['message']}")
    if len(stats['client_errors']) > 5:
        print(f"... et {len(stats['client_errors'])-5} autres erreurs client")
    
    print(f"\n=== Opérations GPU ({len(stats['gpu_operations'])}) ===")
    for op in stats['gpu_operations'][:5]:
        print(f"{op['timestamp']} - {op['message']}")
    if len(stats['gpu_operations']) > 5:
        print(f"... et {len(stats['gpu_operations'])-5} autres opérations GPU")
    
    print(f"\n=== Opérations de séquence ({len(stats['sequence_operations'])}) ===")
    for op in stats['sequence_operations'][:5]:
        print(f"{op['timestamp']} - {op['message']}")
    if len(stats['sequence_operations']) > 5:
        print(f"... et {len(stats['sequence_operations'])-5} autres opérations de séquence")

def parse_log_lines(lines, patterns, show_unparsed=False):
    """
    Analyse une liste de lignes de log avec des patterns donnés.
    Retourne un dict avec les résultats extraits et éventuellement les lignes non parsées.
    """
    results = {
        'total': None,
        'current': None,
        'unparsed': []
    }
    import re
    total_pat = patterns.get('total')
    current_pat = patterns.get('current')
    if total_pat:
        total_pat = re.compile(total_pat)
    if current_pat:
        current_pat = re.compile(current_pat)
    for line in lines:
        matched = False
        if total_pat:
            m = total_pat.search(line)
            if m:
                results['total'] = int(m.group(1))
                matched = True
        if current_pat:
            m = current_pat.search(line)
            if m:
                # On suppose 3 groupes: idx, total, item
                results['current'] = {
                    'idx': int(m.group(1)),
                    'total': int(m.group(2)),
                    'item': m.group(3)
                }
                matched = True
        if not matched and show_unparsed:
            results['unparsed'].append(line)
    return results

def main():
    parser = argparse.ArgumentParser(description='Analyseur de logs pour l\'application de workflow')
    parser.add_argument('log_file', help='Chemin vers le fichier de log à analyser')
    parser.add_argument('--filter', action='store_true', help='Filtrer les logs')
    parser.add_argument('--analyze', action='store_true', help='Analyser les logs et générer des statistiques')
    parser.add_argument('--level', help='Filtrer par niveau (INFO, WARNING, ERROR, etc.)')
    parser.add_argument('--module', help='Filtrer par module')
    parser.add_argument('--thread', help='Filtrer par thread')
    parser.add_argument('--message', help='Filtrer par motif dans le message')
    parser.add_argument('--start-time', help='Filtrer à partir de cette date/heure (format: YYYY-MM-DD HH:MM:SS)')
    parser.add_argument('--end-time', help='Filtrer jusqu\'à cette date/heure (format: YYYY-MM-DD HH:MM:SS)')
    parser.add_argument('--format', choices=['text', 'json', 'csv'], default='text', help='Format de sortie')
    parser.add_argument('--output', help='Fichier de sortie (par défaut: stdout)')
    parser.add_argument('--show-unparsed', action='store_true', help='Afficher les lignes non reconnues')

    args = parser.parse_args()

    if args.filter:
        start_time = None
        if args.start_time:
            try:
                start_time = datetime.strptime(args.start_time, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                print(f"Format de date/heure invalide pour --start-time: {args.start_time}")
                return
        end_time = None
        if args.end_time:
            try:
                end_time = datetime.strptime(args.end_time, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                print(f"Format de date/heure invalide pour --end-time: {args.end_time}")
                return
        filter_logs(
            args.log_file,
            output_format=args.format,
            level=args.level,
            module=args.module,
            thread=args.thread,
            message_pattern=args.message,
            start_time=start_time,
            end_time=end_time,
            output_file=args.output,
            show_unparsed=args.show_unparsed
        )
    if args.analyze:
        analyze_logs(args.log_file)
    
    if not args.filter and not args.analyze:
        parser.print_help()

if __name__ == '__main__':
    main()
