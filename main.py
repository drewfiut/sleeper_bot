import requests
from cache import JSONCache
from creds import OPEN_AI_KEY, DISC_URL

FF_WEEK_END = 0


def main():

    lvflId = "1130284479609847808"
    stumbFumb = "982062951139983360"
    chrungID = "930716840920227840"

    leagueId = lvflId

    updateStartWeek()

    if(FF_WEEK_END == 0):
        print("Week not set. Exiting...")
        return

    # players = loadPlayerData()
    info = loadLeagueInfo(leagueId)
    # drafts = loadDraftData(leagueId)
    
    prompt = getAiPrompt(info)
    print("Calling AI...")
    summary = getAiReponse(prompt)
    print("Sending Message...")
    postToDiscord(summary)


def getLeagueDetails(info, leagueId) -> dict:
    
    response = requests.get(f"https://api.sleeper.app/v1/league/{leagueId}")

    try: 
        json = response.json()
    except Exception:
        print(f"Sleeper API Error. Exiting...{response}")
        return
    
    
    #print(response.text)
    
    info['name'] = json['name']
    info['team_num'] = json['settings']['num_teams']
    info['playoff_teams'] = json['settings']['playoff_teams']
    info['playoff_week_start'] = json['settings']['playoff_week_start']


    return info


def getTeamDetails(info, leagueId) -> dict:

    response = requests.get(f"https://api.sleeper.app/v1/league/{leagueId}/users")

    try: 
        json = response.json()
    except Exception:
        print("Sleeper API Error. Exiting...")
        return
    
    # print(response.text)

    teams = {}

    for user in json:
        userId = user['user_id']
        if user['metadata'].get('team_name') is not None and user['metadata'].get('team_name') != "":
            teamName = user['metadata']['team_name']
        else:
            teamName = user['display_name']
        teams[userId] = {
            'name': user['display_name'],
            #'avatar': user['avatar'],
            'team_name': teamName
        }

    response = requests.get(f"https://api.sleeper.app/v1/league/{leagueId}/rosters")

    try: 
        json = response.json()
    except Exception:
        print(f"Sleeper API Error. Exiting...{response}")
        return
    
    for roster in json:
        teams[roster['owner_id']]['wins'] = str(roster['settings']['wins'])
        teams[roster['owner_id']]['losses'] = str(roster['settings']['losses'])
        teams[roster['owner_id']]['fpts'] = str(roster['settings']['fpts'])
        teams[roster['owner_id']]['fpts_against'] = str(roster['settings']['fpts_against'])
        teams[roster['owner_id']]['roster'] = str(roster['roster_id'])
    
    info['teams'] = teams
    return info


def getMatchupDetails(info, leagueId) -> dict:
    info['matchups'] = {}
    for week in range(1,FF_WEEK_END+1):
        response = requests.get(f"https://api.sleeper.app/v1/league/{leagueId}/matchups/{week}")

        try: 
            json = response.json()
        except Exception:
            print("Sleeper API Error. Exiting...")
            return
        
        matchups = {}
        for team in json:
            teamName = ''
            for infoTeam in info['teams'].values():
                if infoTeam['roster'] == str(team['roster_id']):
                    teamName = infoTeam['team_name']
            if team['matchup_id'] in matchups:
                matchups[team['matchup_id']]['B_name'] = teamName
                matchups[team['matchup_id']]['B_pts'] = str(team['points'])
            else:
                matchups[team['matchup_id']] = {}
                matchups[team['matchup_id']]['A_name'] = teamName
                matchups[team['matchup_id']]['A_pts'] = str(team['points'])
        info['matchups'][str(week)] = matchups
    return info


def getAiPrompt(info) -> str:

    ask = f"Summarize the Week {FF_WEEK_END} standings and key updates for fantasy football. Use paragraphs and bullets. Use the historical matchup data provided to report on any notable season trends. Do not include the standings, but let me know if there were any changes in the standings since the previous week. Use less than 2000 characters in your response, including formatting characters and white space. Use only markdown characters available to discord. Take your time to read all the data provided and formulate your response.\n"
    leagueInfo = f"League Overview\nLeague Name: {info['name']}\nNumber of Teams: {info['team_num']}\nNumber of Teams that can make the playoffs: {info['playoff_teams']}\nWeek of first playoff match: {info['playoff_week_start']}"
    teamInfo = "Team Information\n"
    for team in info['teams'].values():
        teamInfo = f"{teamInfo}\nTeam Name: {team['team_name']}\nTeam Owner: {team['name']}\nWins: {team['wins']}\nLosses: {team['losses']}\nPoints For: {team['fpts']}\nPoints Against: {team['fpts_against']}\n"

    matchupInfo = "Matchup History\n"
    for matchupWeek in info['matchups']:
            matchupInfo = f"{matchupInfo}\n\nWeek {matchupWeek}"
            for matchup in info['matchups'][matchupWeek].values():
                matchupInfo = f"{matchupInfo}\n{matchup['A_name']} ({matchup['A_pts']}) vs {matchup['B_name']} ({matchup['B_pts']})"
    return f"{ask}\n{leagueInfo}\n{teamInfo}\n{matchupInfo}"
    # return f"{ask}\nHere is the league information: {info}"


def getAiReponse(prompt) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=OPEN_AI_KEY)

    response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "You are a helpful fantasy football assistant. You are fun with an edgy personality. You love to make unique jokes and talk smack in your responses."},
        {"role": "user", "content": prompt},
    ]
    )

    message = response.choices[0].message.content
    return message


def postToDiscord(msg):

    payload = {
        'content': msg[0:2000],
    }
    request = requests.post(DISC_URL, json=payload)
    print(request)
    print(request.text)


def loadPlayerData() -> dict:

    cache = JSONCache(f"./cache/players_cache.json", ttl=86400)  # 1 hour TTL
    cached_data = cache.get()
    if cached_data is None:
        # Cache is empty or expired, fetch fresh data
        print("Player cache miss.")
        response = requests.get(f"https://api.sleeper.app/v1/players/nfl")
        try: 
            players = response.json()
        except Exception:
            print(f"Sleeper API Error. Exiting...{response}")
            return
        cache.set(players)  # Save the fresh data to cache
    else:
        print("Player cache hit!")
        players = cached_data
    
    return players


def loadLeagueInfo(leagueId) -> dict:
    cache = JSONCache(f"./cache/{leagueId}_cache.json", ttl=3600)  # 1 hour TTL
    cached_data = cache.get()
    if cached_data is None:
        # Cache is empty or expired, fetch fresh data
        print("League cache miss.")
        info = {}
        print("Getting League Details...")
        getLeagueDetails(info, leagueId)
        print("Getting Team Details...")
        getTeamDetails(info, leagueId)
        print("Getting Matchup Details...")
        getMatchupDetails(info, leagueId)
        cache.set(info)  # Save the fresh data to cache
    else:
        print("League cache hit!")
        info = cached_data

    return info


def loadDraftData(leagueId) -> dict:

    cache = JSONCache(f"./cache/{leagueId}_drafts_cache.json", ttl=86400)  # 1 hour TTL
    cached_data = cache.get()
    if cached_data is None:
        # Cache is empty or expired, fetch fresh data
        print("Drafts cache miss.")
        response = requests.get(f"https://api.sleeper.app/v1/league/{leagueId}/drafts")
        try: 
            drafts = response.json()
        except Exception:
            print(f"Sleeper API Error. Exiting...{response}")
            return
        cache.set(drafts)  # Save the fresh data to cache
    else:
        print("Drafts cache hit!")
        drafts = cached_data
    
    draftId = drafts[0]['draft_id']
    cache = JSONCache(f"./cache/{draftId}_draft_cache.json", ttl=86400)  # 1 hour TTL
    cached_data = cache.get()
    if cached_data is None:
        # Cache is empty or expired, fetch fresh data
        print("Draft cache miss.")
        response = requests.get(f"https://api.sleeper.app/v1/draft/{draftId}/picks")
        try: 
            draft = response.json()
        except Exception:
            print(f"Sleeper API Error. Exiting...{response}")
            return
        cache.set(draft)  # Save the fresh data to cache
    else:
        print("Draft cache hit!")
        draft = cached_data

    return draft


def updateStartWeek() -> None:
    response = requests.get(f"https://api.sleeper.app/v1/state/nfl")

    try: 
        json = response.json()
    except Exception:
        print("Sleeper API Error. Exiting...")
        return

    global FF_WEEK_END
    FF_WEEK_END = json['week'] - 1


if __name__ == "__main__":
    main()