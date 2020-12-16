class EqualSets:
    def __init__(self, data):
        self.data = set(data)

    def __eq__(self, ref):
        return set(ref) == self.data


def update_all_tags(all_agents, connections):
    for i in connections:
        if "agent_tags" in i["agent_1"]:
            all_agents[i["agent_1"]["agent_id"]]["agent_tags"] = i["agent_1"][
                "agent_tags"
            ]
        if "agent_tags" in i["agent_2"]:
            all_agents[i["agent_2"]["agent_id"]]["agent_tags"] = i["agent_2"][
                "agent_tags"
            ]
