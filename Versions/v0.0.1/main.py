from flask import Flask, render_template, request, jsonify
import requests
from dotenv import load_dotenv
import os
from datetime import datetime

app = Flask(__name__)
load_dotenv()

RIOT_API_KEY = os.getenv('RIOT_API_KEY')
RIOT_HEADERS = {
    'X-Riot-Token': RIOT_API_KEY
}

# Region routing data
REGIONS = {
    'europe': {
        'platform': 'euw1',
        'region': 'europe',
        'name': 'Europe West'
    },
    'americas': {
        'platform': 'na1',
        'region': 'americas',
        'name': 'North America'
    },
    'asia': {
        'platform': 'kr',
        'region': 'asia',
        'name': 'Korea'
    },
    'sea': {
        'platform': 'jp1',
        'region': 'sea',
        'name': 'Japan'
    }
}

def get_region_urls(region_code='europe'):
    region = REGIONS.get(region_code, REGIONS['europe'])
    return {
        'account': f"https://{region['region']}.api.riotgames.com",
        'platform': f"https://{region['platform']}.api.riotgames.com"
    }

def get_account_by_riot_id(game_name, tag_line, region='europe'):
    """Get account information using Riot ID"""
    urls = get_region_urls(region)
    url = f"{urls['account']}/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
    response = requests.get(url, headers=RIOT_HEADERS)
    if response.status_code == 200:
        return response.json()
    return None

def get_match_list(puuid, region='europe', count=20):
    """Get list of match IDs for a player"""
    urls = get_region_urls(region)
    url = f"{urls['account']}/lol/match/v5/matches/by-puuid/{puuid}/ids?start=0&count={count}"
    response = requests.get(url, headers=RIOT_HEADERS)
    if response.status_code == 200:
        return response.json()
    return []

def get_match_details(match_id, region='europe'):
    """Get detailed information about a specific match"""
    urls = get_region_urls(region)
    url = f"{urls['account']}/lol/match/v5/matches/{match_id}"
    response = requests.get(url, headers=RIOT_HEADERS)
    if response.status_code == 200:
        return response.json()
    return None

def process_match_data(matches_data, puuid):
    """Process match data to get player statistics"""
    # Podstawowe liczniki
    total_kills = 0
    total_deaths = 0
    total_assists = 0
    wins = 0
    total_games = 0
    total_gold = 0
    total_cs = 0
    total_vision_score = 0
    total_damage_dealt = 0
    total_damage_taken = 0
    total_time_played = 0
    total_turret_kills = 0
    total_inhibitor_kills = 0
    total_double_kills = 0
    total_triple_kills = 0
    total_quadra_kills = 0
    total_penta_kills = 0
    
    # Słowniki do śledzenia statystyk
    champions_played = {}
    roles_played = {}
    items_frequency = {}  # Najczęściej kupowane przedmioty
    role_stats = {  # Statystyki per rola
        'TOP': {'games': 0, 'wins': 0, 'kills': 0, 'deaths': 0, 'assists': 0, 'cs': 0},
        'JUNGLE': {'games': 0, 'wins': 0, 'kills': 0, 'deaths': 0, 'assists': 0, 'cs': 0},
        'MIDDLE': {'games': 0, 'wins': 0, 'kills': 0, 'deaths': 0, 'assists': 0, 'cs': 0},
        'BOTTOM': {'games': 0, 'wins': 0, 'kills': 0, 'deaths': 0, 'assists': 0, 'cs': 0},
        'UTILITY': {'games': 0, 'wins': 0, 'kills': 0, 'deaths': 0, 'assists': 0, 'cs': 0}
    }
    champion_stats = {}  # Statystyki per champion
    cs_per_min_trend = []  # Trend CS na minutę
    position_stats = []  # Statystyki pozycji na mapie
    
    for match in matches_data:
        if not match:
            continue
            
        participant = next((p for p in match['info']['participants'] 
                          if p['puuid'] == puuid), None)
                
        if not participant:
            continue
            
        game_duration_minutes = match['info']['gameDuration'] / 60
        total_games += 1
        total_kills += participant['kills']
        total_deaths += participant['deaths']
        total_assists += participant['assists']
        total_gold += participant['goldEarned']
        current_cs = participant['totalMinionsKilled'] + participant.get('neutralMinionsKilled', 0)
        total_cs += current_cs
        total_vision_score += participant.get('visionScore', 0)
        total_damage_dealt += participant['totalDamageDealtToChampions']
        total_damage_taken += participant['totalDamageTaken']
        total_time_played += match['info']['gameDuration']
        total_turret_kills += participant.get('turretKills', 0)
        total_inhibitor_kills += participant.get('inhibitorKills', 0)
        total_double_kills += participant.get('doubleKills', 0)
        total_triple_kills += participant.get('tripleKills', 0)
        total_quadra_kills += participant.get('quadraKills', 0)
        total_penta_kills += participant.get('pentaKills', 0)
        
        # Zapisz trend CS/min
        cs_per_min = current_cs / game_duration_minutes if game_duration_minutes > 0 else 0
        cs_per_min_trend.append({
            'gameId': match['metadata']['matchId'],
            'csPerMin': round(cs_per_min, 2),
            'timestamp': match['info']['gameStartTimestamp']
        })
        
        # Zbierz statystyki pozycji na mapie
        if 'challenges' in participant and 'teamDamagePercentage' in participant['challenges'] and participant.get('individualPosition', 'UNKNOWN') != 'UNKNOWN':
            position_stats.append({
                'x': participant.get('individualPosition'),
                'y': participant['challenges']['teamDamagePercentage'],
                'value': participant['totalDamageDealtToChampions']
            })
        
        # Aktualizuj statystyki championów
        champion = participant['championName']
        if champion not in champion_stats:
            champion_stats[champion] = {
                'games': 0,
                'wins': 0,
                'kills': 0,
                'deaths': 0,
                'assists': 0,
                'cs': 0,
                'damage': 0,
                'gold': 0
            }
        
        champion_stats[champion]['games'] += 1
        if participant['win']:
            champion_stats[champion]['wins'] += 1
        champion_stats[champion]['kills'] += participant['kills']
        champion_stats[champion]['deaths'] += participant['deaths']
        champion_stats[champion]['assists'] += participant['assists']
        champion_stats[champion]['cs'] += current_cs
        champion_stats[champion]['damage'] += participant['totalDamageDealtToChampions']
        champion_stats[champion]['gold'] += participant['goldEarned']
        
        # Aktualizuj statystyki przedmiotów
        for i in range(0, 7):  # 6 slotów na przedmioty + ward
            item_id = participant.get(f'item{i}', 0)
            if item_id > 0:
                if item_id in items_frequency:
                    items_frequency[item_id] += 1
                else:
                    items_frequency[item_id] = 1
        
        # Aktualizuj statystyki ról
        role = participant.get('teamPosition', 'UNKNOWN')
        if role in role_stats:
            role_stats[role]['games'] += 1
            if participant['win']:
                role_stats[role]['wins'] += 1
            role_stats[role]['kills'] += participant['kills']
            role_stats[role]['deaths'] += participant['deaths']
            role_stats[role]['assists'] += participant['assists']
            role_stats[role]['cs'] += current_cs
        
        if participant['win']:
            wins += 1
            
        if champion in champions_played:
            champions_played[champion] += 1
        else:
            champions_played[champion] = 1
            
        if role in roles_played:
            roles_played[role] += 1
        else:
            roles_played[role] = 1
    
    # Oblicz statystyki
    win_rate = (wins / total_games * 100) if total_games > 0 else 0
    kda = ((total_kills + total_assists) / total_deaths) if total_deaths > 0 else (total_kills + total_assists)
    avg_game_duration = total_time_played / total_games if total_games > 0 else 0
    
    # Sortowanie i formatowanie danych
    most_played_champions = sorted(champions_played.items(), key=lambda x: x[1], reverse=True)[:3]
    most_played_roles = sorted(roles_played.items(), key=lambda x: x[1], reverse=True)
    most_common_items = sorted(items_frequency.items(), key=lambda x: x[1], reverse=True)[:10]
    
    # Przetworzone statystyki championów
    processed_champion_stats = {}
    for champ, stats in champion_stats.items():
        games = stats['games']
        processed_champion_stats[champ] = {
            'games': games,
            'winRate': (stats['wins'] / games * 100) if games > 0 else 0,
            'avgKills': stats['kills'] / games if games > 0 else 0,
            'avgDeaths': stats['deaths'] / games if games > 0 else 0,
            'avgAssists': stats['assists'] / games if games > 0 else 0,
            'avgCs': stats['cs'] / games if games > 0 else 0,
            'avgDamage': stats['damage'] / games if games > 0 else 0,
            'avgGold': stats['gold'] / games if games > 0 else 0
        }
    
    # Przetworzone statystyki ról
    processed_role_stats = {}
    for role, stats in role_stats.items():
        games = stats['games']
        if games > 0:
            processed_role_stats[role] = {
                'games': games,
                'winRate': (stats['wins'] / games * 100) if games > 0 else 0,
                'avgKills': stats['kills'] / games,
                'avgDeaths': stats['deaths'] / games,
                'avgAssists': stats['assists'] / games,
                'avgCs': stats['cs'] / games
            }
    
    # Średnie statystyki na grę
    avg_stats = {
        'kills': total_kills / total_games if total_games > 0 else 0,
        'deaths': total_deaths / total_games if total_games > 0 else 0,
        'assists': total_assists / total_games if total_games > 0 else 0,
        'cs': total_cs / total_games if total_games > 0 else 0,
        'gold': total_gold / total_games if total_games > 0 else 0,
        'vision_score': total_vision_score / total_games if total_games > 0 else 0,
        'damage_dealt': total_damage_dealt / total_games if total_games > 0 else 0,
        'damage_taken': total_damage_taken / total_games if total_games > 0 else 0,
    }
    
    return {
        'games_played': total_games,
        'wins': wins,
        'losses': total_games - wins,
        'win_rate': f"{win_rate:.1f}%",
        'total_kills': total_kills,
        'total_deaths': total_deaths,
        'total_assists': total_assists,
        'kda_ratio': f"{kda:.2f}",
        'most_played_champions': most_played_champions,
        'most_played_roles': most_played_roles,
        
        # Średnie statystyki
        'avg_game_duration': f"{int(avg_game_duration // 60)}:{int(avg_game_duration % 60):02d}",
        'avg_stats': {
            'kills': f"{avg_stats['kills']:.1f}",
            'deaths': f"{avg_stats['deaths']:.1f}",
            'assists': f"{avg_stats['assists']:.1f}",
            'cs': f"{avg_stats['cs']:.1f}",
            'gold': f"{avg_stats['gold']:.0f}",
            'vision_score': f"{avg_stats['vision_score']:.1f}",
            'damage_dealt': f"{avg_stats['damage_dealt']:.0f}",
            'damage_taken': f"{avg_stats['damage_taken']:.0f}",
        },
        
        # Statystyki wielokrotnych zabójstw
        'multikills': {
            'double_kills': total_double_kills,
            'triple_kills': total_triple_kills,
            'quadra_kills': total_quadra_kills,
            'penta_kills': total_penta_kills
        },
        
        # Statystyki obiektów
        'objectives': {
            'turret_kills': total_turret_kills,
            'inhibitor_kills': total_inhibitor_kills
        },
        
        # Nowe statystyki
        'champion_stats': processed_champion_stats,
        'role_stats': processed_role_stats,
        'most_common_items': most_common_items,
        'cs_trend': sorted(cs_per_min_trend, key=lambda x: x['timestamp']),
        'position_stats': position_stats
    }

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/search_player', methods=['POST'])
def search_player():
    data = request.json
    riot_id = data.get('summonerName', '').strip()
    region = data.get('region', 'europe').strip()
    
    if region not in REGIONS:
        return jsonify({'error': 'Invalid region selected'}), 400
        
    if '#' not in riot_id:
        return jsonify({'error': 'Please provide Riot ID in format: Name#Tag'}), 400
        
    game_name, tag_line = riot_id.split('#')
    
    # Get account information (PUUID)
    account_info = get_account_by_riot_id(game_name, tag_line, region)
    if not account_info:
        return jsonify({'error': 'Player not found'}), 404
        
    # Get match list
    match_ids = get_match_list(account_info['puuid'], region)
    if not match_ids:
        return jsonify({'error': 'No recent matches found'}), 404
        
    # Get match details
    matches_data = []
    for match_id in match_ids:
        match_data = get_match_details(match_id, region)
        if match_data:
            matches_data.append(match_data)
            
    # Get overall statistics
    stats = process_match_data(matches_data, account_info['puuid'])
            
    # Process match data for the response
    matches = []
    for match in matches_data:
        participant = next((p for p in match['info']['participants'] 
                          if p['puuid'] == account_info['puuid']), None)
        if participant:
            matches.append({
                'matchId': match['metadata']['matchId'],
                'championName': participant['championName'],
                'championIcon': f"http://ddragon.leagueoflegends.com/cdn/13.24.1/img/champion/{participant['championName']}.png",
                'win': participant['win'],
                'kills': participant['kills'],
                'deaths': participant['deaths'],
                'assists': participant['assists'],
                'kda': f"{((participant['kills'] + participant['assists']) / max(1, participant['deaths'])):.2f}",
                'cs': participant['totalMinionsKilled'] + participant.get('neutralMinionsKilled', 0),
                'gameMode': match['info']['gameMode'],
                'gameDuration': f"{match['info']['gameDuration'] // 60}:{match['info']['gameDuration'] % 60:02d}",
                'gameDate': datetime.fromtimestamp(match['info']['gameStartTimestamp'] / 1000).strftime('%Y-%m-%d %H:%M')
            })
    
    response_data = {
        'summonerName': account_info['gameName'],
        'tagLine': account_info['tagLine'],
        'region': region,
        'summonerLevel': account_info.get('summonerLevel', 0),
        'matches': matches,
        **stats  # Add overall statistics to the response
    }
    
    return jsonify(response_data)

@app.route('/match/<match_id>')
def get_match(match_id):
    region = request.args.get('region', 'europe')
    match_data = get_match_details(match_id, region)
    if match_data:
        return jsonify(match_data)
    return jsonify({'error': 'Match not found'}), 404

if __name__ == '__main__':
    if not RIOT_API_KEY:
        print("Please set your RIOT_API_KEY in the .env file")
        exit(1)
    app.run(debug=True)