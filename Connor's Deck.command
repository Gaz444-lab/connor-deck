#!/bin/zsh
# Double-click to start Connor's Deck
cd "$(dirname "$0")"
./launch.sh
echo ""
echo "Deck is running. Leave this window open while you use it,"
echo "or close it — the server keeps going in the background."
echo "To stop later: double-click Stop Deck.command"
echo ""
read -r "?Press Enter to close this window… "
