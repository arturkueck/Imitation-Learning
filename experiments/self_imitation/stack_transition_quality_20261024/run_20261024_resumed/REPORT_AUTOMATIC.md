# Automatischer B0/B-Laufbericht

QualitÃƒÂ¤tsgewichtung gegen Einheitsgewichtung; kein FÃƒÂ¼nfertraining und keine Erfolgsprognose.

## session.json

```json

{
  "start": 1792863317.672519,
  "deadline": 1792892117.672519,
  "training_deadline": 1792881317.672519,
  "resumed_at": 1792873590.6898355,
  "supervisor_pid": 25916,
  "plan_sha256": "cd3f35a1462435d0cfe072a27908b4e9622328ba7e55a70d43308fb6c93e32eb"
}

```

## status.json

```json

{
  "state": "COMPLETE",
  "result_groups": 12,
  "finished_unix": 1792881973.292382
}

```

## supervisor_status.json

```json

{
  "state": "COMPLETED",
  "pid": 25916,
  "deadline": 1792892117.672519,
  "worker_pid": 11280,
  "heartbeat_unix": 1792881972.5581987,
  "returncode": 0,
  "finished_unix": 1792881974.5590005,
  "wake_lock_released": true
}

```

## training/status.json

```json

{
  "state": "COMPLETE",
  "completed_round": 10000,
  "updates": {
    "B0_seed1": 10000,
    "B_seed1": 10000,
    "B0_seed2": 10000,
    "B_seed2": 10000,
    "B0_seed3": 10000,
    "B_seed3": 10000
  },
  "technical_only": false
}

```

## VollstÃƒÂ¤ndige und teilweise Endauswertungen

| Modell/Split | Metrik | Erfolge | Versuche | vollstÃƒÂ¤ndig |

|---|---|---:|---:|---|

| B0_seed1_confirmation | prepared_prefix2 | 4 | 20 | True |

| B0_seed1_confirmation | prepared_prefix3 | 4 | 20 | True |

| B0_seed1_reserved_final | prepared_prefix2 | 17 | 50 | True |

| B0_seed1_reserved_final | prepared_prefix3 | 7 | 50 | True |

| B0_seed1_reserved_final | full_stack2 | 50 | 50 | True |

| B0_seed1_reserved_final | full_stack3 | 57 | 100 | True |

| B0_seed1_reserved_final | full_stack4 | 28 | 100 | True |

| B0_seed2_confirmation | prepared_prefix2 | 3 | 20 | True |

| B0_seed2_confirmation | prepared_prefix3 | 3 | 20 | True |

| B0_seed2_reserved_final | prepared_prefix2 | 14 | 50 | True |

| B0_seed2_reserved_final | prepared_prefix3 | 7 | 50 | True |

| B0_seed2_reserved_final | full_stack2 | 50 | 50 | True |

| B0_seed2_reserved_final | full_stack3 | 50 | 100 | True |

| B0_seed2_reserved_final | full_stack4 | 22 | 100 | True |

| B0_seed3_confirmation | prepared_prefix2 | 1 | 20 | True |

| B0_seed3_confirmation | prepared_prefix3 | 3 | 20 | True |

| B0_seed3_reserved_final | prepared_prefix2 | 10 | 50 | True |

| B0_seed3_reserved_final | prepared_prefix3 | 9 | 50 | True |

| B0_seed3_reserved_final | full_stack2 | 48 | 50 | True |

| B0_seed3_reserved_final | full_stack3 | 40 | 100 | True |

| B0_seed3_reserved_final | full_stack4 | 16 | 100 | True |

| B_seed1_confirmation | prepared_prefix2 | 4 | 20 | True |

| B_seed1_confirmation | prepared_prefix3 | 4 | 20 | True |

| B_seed1_reserved_final | prepared_prefix2 | 17 | 50 | True |

| B_seed1_reserved_final | prepared_prefix3 | 7 | 50 | True |

| B_seed1_reserved_final | full_stack2 | 50 | 50 | True |

| B_seed1_reserved_final | full_stack3 | 57 | 100 | True |

| B_seed1_reserved_final | full_stack4 | 28 | 100 | True |

| B_seed2_confirmation | prepared_prefix2 | 3 | 20 | True |

| B_seed2_confirmation | prepared_prefix3 | 3 | 20 | True |

| B_seed2_reserved_final | prepared_prefix2 | 14 | 50 | True |

| B_seed2_reserved_final | prepared_prefix3 | 7 | 50 | True |

| B_seed2_reserved_final | full_stack2 | 50 | 50 | True |

| B_seed2_reserved_final | full_stack3 | 50 | 100 | True |

| B_seed2_reserved_final | full_stack4 | 22 | 100 | True |

| B_seed3_confirmation | prepared_prefix2 | 1 | 20 | True |

| B_seed3_confirmation | prepared_prefix3 | 3 | 20 | True |

| B_seed3_reserved_final | prepared_prefix2 | 10 | 50 | True |

| B_seed3_reserved_final | prepared_prefix3 | 9 | 50 | True |

| B_seed3_reserved_final | full_stack2 | 48 | 50 | True |

| B_seed3_reserved_final | full_stack3 | 40 | 100 | True |

| B_seed3_reserved_final | full_stack4 | 16 | 100 | True |

Fehlende Tests sind ungemessen. Nicht abgeschlossene Starts werden weder als Erfolg noch als Misserfolg erfunden. In evaluation_progress liegen inkrementelle Teilresultate; reservierte Starts werden nicht automatisch wiederholt.

Die Auswahl wurde vor BestÃƒÂ¤tigung/Endtest gemeinsam eingefroren; Einzelheiten und VollstÃƒÂ¤ndigkeit stehen in final_test/selection.json.

Historische Quoten mit fehlerhafter FingerkontaktprÃƒÂ¼fung sind keine direkte Referenz fÃƒÂ¼r diese korrigierte Metrik.