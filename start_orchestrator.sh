  #!/bin/bash
  cd ~/TicketingSDT

  # Load environment variables properly (handles special characters)
  set -a
  source .env
  set +a

  python3 main.py
  EOF

