# Channel states

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│    ┌─────────┐      Node sends packet      ┌─────────┐ │
│    │         │ ───────────────────────────▶│         │ │
│    │  CLEAR  │                             │  BUSY   │ │
│    │         │◀─────────────────────────── │         │ │
│    └─────────┘   Transmission complete     └─────────┘ │
│                  Deliver to nodes in range             │
│                                                         │
└─────────────────────────────────────────────────────────┘
```


# Node states (sender)

```
With probability P
                          generate DATA packet
                                  │
                                  ▼
                    ┌─────────────────────────┐
                    │     Channel busy?       │
                    └─────────────────────────┘
                         │              │
                        YES             NO
                         │              │
                         ▼              ▼
              ┌──────────────┐   ┌──────────────┐
              │   WAITING    │   │  DIFS WAIT   │
              │  FOR CLEAR   │   │              │
              └──────────────┘   └──────────────┘
                     │                  │
                     │   Channel free   │ DIFS expires
                     └───────┬──────────┘
                             ▼
                    ┌──────────────┐
                    │  CONTENTION  │◀──────────────────┐
                    │   WINDOW     │                   │
                    │  (Backoff)   │                   │
                    └──────────────┘                   │
                             │                        │
                             │ Backoff expires        │
                             ▼                        │
                    ┌──────────────┐                  │
                    │ TRANSMIT RTS │                  │
                    └──────────────┘                  │
                             │                        │
                             │ RTS sent               │
                             ▼                        │
                    ┌──────────────┐                  │
                    │ WAITING FOR  │                  │
                    │     CTS      │                  │
                    └──────────────┘                  │
                        │       │                     │
              CTS received     Timeout                │
                        │       │                     │
                        ▼       └──────┐              │
                ┌──────────────┐       │              │
                │  SIFS WAIT   │       ▼              │
                └──────────────┘  ┌─────────┐         │
                        │         │ TIMEOUT │         │
                        │         │ Double  │         │
                        ▼         │   CW    │         │
                ┌──────────────┐  └─────────┘         │
                │TRANSMIT DATA │       │              │
                └──────────────┘       └──────────────┘
                        │
                        │ DATA sent
                        ▼
                ┌──────────────┐
                │ WAITING FOR  │
                │     ACK      │
                └──────────────┘
                        │
                        │ ACK received
                        ▼
                ┌──────────────┐
                │     IDLE     │  ✓ Success!
                └──────────────┘
```


# Node states (receiver)

```
                ┌──────────────┐
                │     IDLE     │
                └──────────────┘
                        │
                        │ RTS received (addressed to me)
                        ▼
                ┌──────────────┐
                │  SIFS WAIT   │
                └──────────────┘
                        │
                        │ SIFS expires
                        ▼
                ┌──────────────┐
                │ TRANSMIT CTS │
                └──────────────┘
                        │
                        │ CTS sent
                        ▼
                ┌──────────────┐
                │ WAITING FOR  │
                │    DATA      │
                └──────────────┘
                        │
                        │ DATA received
                        ▼
                ┌──────────────┐
                │  SIFS WAIT   │
                └──────────────┘
                        │
                        │ SIFS expires
                        ▼
                ┌──────────────┐
                │ TRANSMIT ACK │
                └──────────────┘
                        │
                        │ ACK sent
                        ▼
                ┌──────────────┐
                │     IDLE     │  ✓ Reception complete!
                └──────────────┘
```


# Timing sequence

```
SENDER:    ║ DIFS ║ CW ║  RTS  ║         ║ SIFS ║    DATA    ║         ║
           ╠══════╬════╬═══════╬═════════╬══════╬════════════╬═════════╣
           ║      ║    ║   ╲   ║         ║  ╱   ║      ╲     ║         ║
           ║      ║    ║    ╲  ║         ║ ╱    ║       ╲    ║         ║
           ║      ║    ║     ╲ ║         ║╱     ║        ╲   ║         ║
           ╠══════╬════╬═══════╬═════════╬══════╬════════════╬═════════╣
RECEIVER:  ║      ║    ║       ║ SIFS║CTS║      ║            ║SIFS║ACK ║
                                                                    
                                                              SUCCESS! ✓
```


# Backoff

```
First attempt:     CW = CW_MIN
                        │
                   Select random backoff in [0, CW]
                        │
                   ┌────┴────┐
                   │ SUCCESS │ ──────▶ Done
                   └────┬────┘
                        │ TIMEOUT (no response)
                        ▼
                   CW = CW × 2  (double)
                        │
                   Select new random backoff
                        │
                      Retry
```