# Will consider if this DRY piece of code will be better to implement later, if it's only two buttons it's not worth it to abstract away
# However it is repeated in the promotion state with slight difference so we will see...
def apply_action(client_state_actions, base_command, client_game, node, action):
    if action == "accept":
        if base_command == "undo":
            # The sender will sync no need to apply again
            offer_data = {node.CMD: "undo_accept"}
            node.tx(offer_data, shm=True)
            your_turn = client_game.whites_turn == client_game._starting_player
            client_game.undo_move()
            if not your_turn:
                client_game.undo_move()
            sent = 0
            # window.sessionStorage.setItem("undo_request", "false")
            hovered_square = None
            selected_piece_image = None
            selected_piece = None
            first_intent = False
            valid_moves, valid_captures, valid_specials = [], [], []
            right_clicked_squares = []
            drawn_arrows = []
        elif base_command == "draw":
            offer_data = {node.CMD: "draw_accept"}
            node.tx(offer_data, shm=True)
            client_game.forced_end = "Draw by mutual agreement"
            print(client_game.forced_end)
            running = False
            client_game.end_position = True
            client_game.add_end_game_notation(False)
    elif action == "response_received":
        client_game.forced_end = "Draw by mutual agreement"
        print(client_game.forced_end)
        running = False
        client_game.end_position = True
        client_game.add_end_game_notation(False)

def handle_state_actions(client_state_actions, base_command, client_game, node):
    sent_status = base_command + "_sent"
    received_status = base_command + "_received"
    offer_command = base_command + "_offer"
    accept_status = base_command + "_accept"
    accept_executed = accept_status + "_executed"
    deny_status = base_command + "_deny"
    deny_executed = deny_status + "_executed"
    response_received = base_command + "_response_received"
    request_name = base_command + "_request"

    if client_state_actions[base_command] and not client_state_actions[sent_status]:
        offer_data = {node.CMD: offer_command}
        node.tx(offer_data, shm=True)
        client_state_actions[sent_status] = True
    if client_state_actions[accept_status] and client_state_actions[received_status]:
        apply_action(client_state_actions, base_command, client_game, node, "accept")
        client_state_actions[received_status] = False
        client_state_actions[accept_status] = False
        client_state_actions[accept_executed] = True
    if client_state_actions[response_received]:
        apply_action(client_state_actions, base_command, client_game, node, "response_received")
        client_state_actions[sent_status] = False
        client_state_actions[response_received] = False
        client_state_actions[base_command] = False
        client_state_actions[accept_executed] = True
    if client_state_actions[deny_status]:
        reset_data = {node.CMD: "reset"}
        node.tx(reset_data, shm=True)
        client_state_actions[deny_status] = False
        client_state_actions[deny_executed] = True
        client_state_actions[received_status] = False
        # window.sessionStorage.setItem(request_name, "false")
# This loop can replace that later section
# for client_status in ["undo", "draw"]:
#     handle_state_actions(client_state_actions, client_status, client_game, node)