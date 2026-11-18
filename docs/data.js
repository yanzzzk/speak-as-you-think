window.PAGE_DATA = {
 "source": {
  "seeds": [
   "seed1",
   "seed2",
   "seed3"
  ],
  "variants": [
   "independent",
   "fish_history",
   "streaming-round",
   "streaming-round-w4",
   "streaming-round-w1"
  ],
  "texts": 6
 },
 "seams": {
  "table": [
   {
    "lang": "en",
    "kind": "word",
    "n": 138,
    "median": {
     "independent": 0.4482,
     "fish_history": 0.4148,
     "streaming-round": 0.1423,
     "streaming-round-w4": 0.1631,
     "streaming-round-w1": 0.2468
    },
    "mean": {
     "independent": 0.7156,
     "fish_history": 0.4891,
     "streaming-round": 0.206,
     "streaming-round-w4": 0.3507,
     "streaming-round-w1": 0.3565
    }
   },
   {
    "lang": "en",
    "kind": "clause",
    "n": 15,
    "median": {
     "independent": 0.7237,
     "fish_history": 0.7464,
     "streaming-round": 0.6421,
     "streaming-round-w4": 0.6764,
     "streaming-round-w1": 0.703
    },
    "mean": {
     "independent": 0.6854,
     "fish_history": 0.6586,
     "streaming-round": 0.518,
     "streaming-round-w4": 0.601,
     "streaming-round-w1": 0.7254
    }
   },
   {
    "lang": "en",
    "kind": "sentence",
    "n": 39,
    "median": {
     "independent": 0.7736,
     "fish_history": 0.6847,
     "streaming-round": 0.856,
     "streaming-round-w4": 0.9192,
     "streaming-round-w1": 0.9758
    },
    "mean": {
     "independent": 0.7774,
     "fish_history": 0.6558,
     "streaming-round": 0.8664,
     "streaming-round-w4": 0.9344,
     "streaming-round-w1": 1.0227
    }
   },
   {
    "lang": "zh",
    "kind": "clause",
    "n": 33,
    "median": {
     "independent": 0.8568,
     "fish_history": 0.7908,
     "streaming-round": 0.7358,
     "streaming-round-w4": 0.7101,
     "streaming-round-w1": 0.7823
    },
    "mean": {
     "independent": 0.8392,
     "fish_history": 0.7228,
     "streaming-round": 0.7013,
     "streaming-round-w4": 0.6631,
     "streaming-round-w1": 0.7563
    }
   },
   {
    "lang": "zh",
    "kind": "sentence",
    "n": 21,
    "median": {
     "independent": 0.7982,
     "fish_history": 0.8326,
     "streaming-round": 0.8888,
     "streaming-round-w4": 0.9087,
     "streaming-round-w1": 1.0074
    },
    "mean": {
     "independent": 0.7358,
     "fish_history": 0.7662,
     "streaming-round": 0.9087,
     "streaming-round-w4": 0.9405,
     "streaming-round-w1": 1.0549
    }
   }
  ],
  "first_seam": {
   "n": 9,
   "median": {
    "independent": 0.4783,
    "fish_history": 0.4783,
    "streaming-round": 0.7218,
    "streaming-round-w4": 0.6207,
    "streaming-round-w1": 0.7155
   }
  },
  "later_seams": {
   "n": 129,
   "median": {
    "independent": 0.447,
    "fish_history": 0.4049,
    "streaming-round": 0.13,
    "streaming-round-w4": 0.1426,
    "streaming-round-w1": 0.2242
   }
  },
  "mean_without_failed": {
   "independent": 0.5265,
   "fish_history": 0.4829,
   "streaming-round": 0.2139,
   "streaming-round-w4": 0.2233,
   "streaming-round-w1": 0.3729
  },
  "n_without_failed": 126,
  "share_over_0p3": {
   "independent": 0.7754,
   "fish_history": 0.6884,
   "streaming-round": 0.2464,
   "streaming-round-w4": 0.2899,
   "streaming-round-w1": 0.4348
  },
  "paired_mid_phrase": {
   "independent": {
    "shorter": 117,
    "longer": 20,
    "of": 138
   },
   "fish_history": {
    "shorter": 117,
    "longer": 17,
    "of": 138
   },
   "streaming-round-w4": {
    "shorter": 61,
    "longer": 54,
    "of": 138
   },
   "streaming-round-w1": {
    "shorter": 84,
    "longer": 43,
    "of": 138
   }
  },
  "paired_first_seam": {
   "independent": {
    "shorter": 6,
    "longer": 3,
    "of": 9
   },
   "fish_history": {
    "shorter": 5,
    "longer": 4,
    "of": 9
   },
   "streaming-round-w4": {
    "shorter": 4,
    "longer": 5,
    "of": 9
   },
   "streaming-round-w1": {
    "shorter": 4,
    "longer": 5,
    "of": 9
   }
  },
  "paired_mid_phrase_last_round": {
   "independent": {
    "shorter": 87,
    "longer": 49,
    "of": 138
   },
   "fish_history": {
    "shorter": 91,
    "longer": 47,
    "of": 138
   },
   "streaming-round": {
    "shorter": 43,
    "longer": 84,
    "of": 138
   },
   "streaming-round-w4": {
    "shorter": 39,
    "longer": 79,
    "of": 138
   }
  },
  "paired_mid_sentence": {
   "independent": {
    "shorter": 153,
    "longer": 32,
    "of": 186
   },
   "fish_history": {
    "shorter": 147,
    "longer": 34,
    "of": 186
   },
   "streaming-round-w4": {
    "shorter": 87,
    "longer": 76,
    "of": 186
   },
   "streaming-round-w1": {
    "shorter": 119,
    "longer": 55,
    "of": 186
   }
  },
  "paired_sentence_end": {
   "independent": {
    "shorter": 24,
    "longer": 34,
    "of": 60
   },
   "fish_history": {
    "shorter": 20,
    "longer": 39,
    "of": 60
   },
   "streaming-round-w4": {
    "shorter": 36,
    "longer": 24,
    "of": 60
   },
   "streaming-round-w1": {
    "shorter": 45,
    "longer": 15,
    "of": 60
   }
  }
 },
 "items": {
  "err_en": {
   "independent": 0.0169,
   "fish_history": 0.0094,
   "streaming-round": 0.004,
   "streaming-round-w4": 0.0123,
   "streaming-round-w1": 0.034
  },
  "err_chunk_en": {
   "independent": 0.0321,
   "fish_history": 0.0218,
   "streaming-round": 0.008,
   "streaming-round-w4": 0.0205,
   "streaming-round-w1": 0.0211
  },
  "leak_rate": {
   "independent": 0.0,
   "fish_history": 0.0,
   "streaming-round": 0.0,
   "streaming-round-w4": 0.0,
   "streaming-round-w1": 0.0
  },
  "sim_all": {
   "independent": 0.7597,
   "fish_history": 0.7061,
   "streaming-round": 0.6871,
   "streaming-round-w4": 0.6866,
   "streaming-round-w1": 0.7519
  },
  "sim_first": {
   "independent": 0.7113,
   "fish_history": 0.6801,
   "streaming-round": 0.6847,
   "streaming-round-w4": 0.6956,
   "streaming-round-w1": 0.6999
  },
  "sim_last": {
   "independent": 0.6868,
   "fish_history": 0.6297,
   "streaming-round": 0.5908,
   "streaming-round-w4": 0.5548,
   "streaming-round-w1": 0.6618
  },
  "failed_chunks": {
   "independent": 1,
   "fish_history": 0,
   "streaming-round": 0,
   "streaming-round-w4": 0,
   "streaming-round-w1": 0
  },
  "chunks": {
   "independent": 264,
   "fish_history": 264,
   "streaming-round": 264,
   "streaming-round-w4": 264,
   "streaming-round-w1": 264
  },
  "err_zh": {
   "independent": 0.0027,
   "fish_history": 0.0,
   "streaming-round": 0.0041,
   "streaming-round-w4": 0.0014,
   "streaming-round-w1": 0.0014
  },
  "err_chunk_zh": {
   "independent": 0.0175,
   "fish_history": 0.0221,
   "streaming-round": 0.0112,
   "streaming-round-w4": 0.0046,
   "streaming-round-w1": 0.0022
  },
  "clips": 18,
  "sim_below_independent": {
   "fish_history": 18,
   "streaming-round": 18,
   "streaming-round-w4": 18,
   "streaming-round-w1": 13
  },
  "sim_above_all_rounds": {
   "independent": 18,
   "fish_history": 14,
   "streaming-round-w4": 8,
   "streaming-round-w1": 18
  },
  "utmos": {
   "independent": 3.33,
   "fish_history": 3.37,
   "streaming-round": 3.42
  },
  "utmos_above_independent": {
   "fish_history": 7,
   "streaming-round": 9
  }
 },
 "clips": [
  {
   "text_id": "en_train",
   "lang": "en",
   "seed": 2,
   "first_chunk": 0,
   "chunks": [
    "The train was already moving when",
    "Anna reached the platform, her",
    "bag bouncing against her hip.",
    "She ran anyway, past the empty",
    "benches and the flickering clock,",
    "until the last door was only a",
    "few steps away."
   ],
   "modes": [
    {
     "variant": "independent",
     "file": "audio/en_train_independent.m4a",
     "seconds": 18.9475,
     "speech": [
      [
       0.034,
       2.142
      ],
      [
       3.2239,
       4.5639
      ],
      [
       5.0799,
       5.5239
      ],
      [
       6.3963,
       8.3443
      ],
      [
       8.904,
       9.956
      ],
      [
       10.44,
       11.492
      ],
      [
       11.6904,
       13.8624
      ],
      [
       14.4304,
       16.8264
      ],
      [
       17.1239,
       18.1759
      ]
     ],
     "seams": [
      {
       "t": 3.1579,
       "from": 2.142,
       "to": 3.2239,
       "pause": 1.0819,
       "kind": "word"
      },
      {
       "t": 6.3623,
       "from": 5.5239,
       "to": 6.3963,
       "pause": 0.8724,
       "kind": "word"
      },
      {
       "t": 8.87,
       "from": 8.3442,
       "to": 8.904,
       "pause": 0.5598,
       "kind": "sentence"
      },
      {
       "t": 11.6564,
       "from": 11.492,
       "to": 11.6904,
       "pause": 0.1984,
       "kind": "word"
      },
      {
       "t": 14.3964,
       "from": 13.8624,
       "to": 14.4304,
       "pause": 0.568,
       "kind": "clause"
      },
      {
       "t": 17.0899,
       "from": 16.8263,
       "to": 17.1239,
       "pause": 0.2976,
       "kind": "word"
      }
     ]
    },
    {
     "variant": "fish_history",
     "file": "audio/en_train_fish_history.m4a",
     "seconds": 22.1054,
     "speech": [
      [
       0.034,
       2.142
      ],
      [
       3.2239,
       4.6599
      ],
      [
       5.0799,
       5.4919
      ],
      [
       6.3498,
       8.2018
      ],
      [
       9.1682,
       10.3482
      ],
      [
       10.9922,
       12.1082
      ],
      [
       12.8514,
       13.6794
      ],
      [
       13.8754,
       15.2154
      ],
      [
       16.2415,
       18.6695
      ],
      [
       19.835,
       21.079
      ]
     ],
     "seams": [
      {
       "t": 3.1579,
       "from": 2.142,
       "to": 3.2239,
       "pause": 1.0819,
       "kind": "word"
      },
      {
       "t": 6.3158,
       "from": 5.4919,
       "to": 6.3498,
       "pause": 0.8579,
       "kind": "word"
      },
      {
       "t": 9.1022,
       "from": 8.2018,
       "to": 9.1682,
       "pause": 0.9664,
       "kind": "sentence"
      },
      {
       "t": 12.8174,
       "from": 12.1082,
       "to": 12.8514,
       "pause": 0.7433,
       "kind": "word"
      },
      {
       "t": 16.2075,
       "from": 15.2154,
       "to": 16.2415,
       "pause": 1.0261,
       "kind": "clause"
      },
      {
       "t": 19.737,
       "from": 18.6695,
       "to": 19.835,
       "pause": 1.1654,
       "kind": "word"
      }
     ]
    },
    {
     "variant": "streaming-round-w1",
     "file": "audio/en_train_streaming-round-w1.m4a",
     "seconds": 19.6905,
     "speech": [
      [
       0.002,
       2.014
      ],
      [
       2.6346,
       4.1346
      ],
      [
       5.1424,
       7.1224
      ],
      [
       7.9639,
       8.9519
      ],
      [
       9.7239,
       10.8719
      ],
      [
       11.676,
       13.944
      ],
      [
       14.6626,
       16.7706
      ],
      [
       17.5914,
       18.6754
      ]
     ],
     "seams": [
      {
       "t": 2.6006,
       "from": 2.0139,
       "to": 2.6346,
       "pause": 0.6207,
       "kind": "word"
      },
      {
       "t": 5.1084,
       "from": 4.1346,
       "to": 5.1424,
       "pause": 1.0078,
       "kind": "word"
      },
      {
       "t": 7.8019,
       "from": 7.1223,
       "to": 7.9639,
       "pause": 0.8416,
       "kind": "sentence"
      },
      {
       "t": 11.61,
       "from": 10.8719,
       "to": 11.676,
       "pause": 0.8041,
       "kind": "word"
      },
      {
       "t": 14.6286,
       "from": 13.9439,
       "to": 14.6626,
       "pause": 0.7186,
       "kind": "clause"
      },
      {
       "t": 17.4614,
       "from": 16.7705,
       "to": 17.5914,
       "pause": 0.8209,
       "kind": "word"
      }
     ]
    },
    {
     "variant": "streaming-round",
     "file": "audio/en_train_streaming-round.m4a",
     "seconds": 17.4614,
     "speech": [
      [
       0.034,
       2.302
      ],
      [
       2.5882,
       3.9602
      ],
      [
       4.4442,
       4.9226
      ],
      [
       4.9566,
       6.7446
      ],
      [
       6.9086,
       7.2566
      ],
      [
       7.6388,
       8.6908
      ],
      [
       9.1108,
       10.5883
      ],
      [
       10.6543,
       12.6343
      ],
      [
       13.2229,
       15.4269
      ],
      [
       15.6874,
       16.6754
      ]
     ],
     "seams": [
      {
       "t": 2.5542,
       "from": 2.3019,
       "to": 2.5882,
       "pause": 0.2863,
       "kind": "word"
      },
      {
       "t": 4.9226,
       "from": 4.9226,
       "to": 4.9566,
       "pause": 0.034,
       "kind": "word"
      },
      {
       "t": 7.4768,
       "from": 7.2566,
       "to": 7.6388,
       "pause": 0.3822,
       "kind": "sentence"
      },
      {
       "t": 10.5883,
       "from": 10.5883,
       "to": 10.6543,
       "pause": 0.066,
       "kind": "word"
      },
      {
       "t": 13.1889,
       "from": 12.6342,
       "to": 13.2229,
       "pause": 0.5887,
       "kind": "clause"
      },
      {
       "t": 15.5574,
       "from": 15.4269,
       "to": 15.6874,
       "pause": 0.2604,
       "kind": "word"
      }
     ]
    }
   ]
  },
  {
   "text_id": "en_billing",
   "lang": "en",
   "seed": 1,
   "first_chunk": 7,
   "chunks": [
    "Our system flagged the second charge",
    "automatically, and the refund has",
    "already been approved on our side.",
    "Depending on your bank, it can",
    "take a few business days to show",
    "up. In the meantime, you don't",
    "need to do anything else."
   ],
   "modes": [
    {
     "variant": "independent",
     "file": "audio/en_billing_independent.m4a",
     "seconds": 18.5295,
     "speech": [
      [
       0.034,
       2.366
      ],
      [
       2.7275,
       3.5235
      ],
      [
       3.8155,
       5.1555
      ],
      [
       5.5459,
       7.6859
      ],
      [
       8.2074,
       9.6114
      ],
      [
       9.7434,
       10.4434
      ],
      [
       10.7472,
       12.6632
      ],
      [
       13.3158,
       13.6958
      ],
      [
       14.4998,
       15.3598
      ],
      [
       15.6838,
       16.3198
      ],
      [
       16.6915,
       18.2555
      ]
     ],
     "seams": [
      {
       "t": 2.6935,
       "from": 2.366,
       "to": 2.7275,
       "pause": 0.3616,
       "kind": "word"
      },
      {
       "t": 5.4799,
       "from": 5.1555,
       "to": 5.5459,
       "pause": 0.3904,
       "kind": "word"
      },
      {
       "t": 8.1734,
       "from": 7.6859,
       "to": 8.2074,
       "pause": 0.5216,
       "kind": "sentence"
      },
      {
       "t": 10.6812,
       "from": 10.4434,
       "to": 10.7472,
       "pause": 0.3038,
       "kind": "word"
      },
      {
       "t": 13.2818,
       "from": 12.6631,
       "to": 13.3158,
       "pause": 0.6527,
       "kind": "word"
      },
      {
       "t": 16.6255,
       "from": 16.3198,
       "to": 16.6915,
       "pause": 0.3717,
       "kind": "word"
      }
     ]
    },
    {
     "variant": "fish_history",
     "file": "audio/en_billing_fish_history.m4a",
     "seconds": 21.3624,
     "speech": [
      [
       0.066,
       2.494
      ],
      [
       3.4561,
       4.3161
      ],
      [
       5.0241,
       6.6201
      ],
      [
       7.5893,
       9.7293
      ],
      [
       9.9113,
       11.3473
      ],
      [
       11.5433,
       12.1153
      ],
      [
       12.5583,
       14.6023
      ],
      [
       15.5305,
       15.8785
      ],
      [
       16.6185,
       17.4785
      ],
      [
       17.8345,
       18.5025
      ],
      [
       18.8277,
       20.7437
      ]
     ],
     "seams": [
      {
       "t": 3.3901,
       "from": 2.494,
       "to": 3.4561,
       "pause": 0.9621,
       "kind": "word"
      },
      {
       "t": 7.5233,
       "from": 6.6201,
       "to": 7.5893,
       "pause": 0.9692,
       "kind": "word"
      },
      {
       "t": 9.8453,
       "from": 9.7293,
       "to": 9.9113,
       "pause": 0.182,
       "kind": "sentence"
      },
      {
       "t": 12.4923,
       "from": 12.1152,
       "to": 12.5583,
       "pause": 0.4431,
       "kind": "word"
      },
      {
       "t": 15.4645,
       "from": 14.6023,
       "to": 15.5305,
       "pause": 0.9282,
       "kind": "word"
      },
      {
       "t": 18.7617,
       "from": 18.5025,
       "to": 18.8277,
       "pause": 0.3252,
       "kind": "word"
      }
     ]
    },
    {
     "variant": "streaming-round-w1",
     "file": "audio/en_billing_streaming-round-w1.m4a",
     "seconds": 18.4831,
     "speech": [
      [
       0.034,
       2.206
      ],
      [
       2.8988,
       3.6948
      ],
      [
       3.9548,
       5.4548
      ],
      [
       5.6388,
       7.5548
      ],
      [
       8.7647,
       10.6807
      ],
      [
       11.4438,
       13.3747
      ],
      [
       13.3747,
       13.9807
      ],
      [
       14.2727,
       15.2287
      ],
      [
       15.4247,
       15.8361
      ],
      [
       15.87,
       17.658
      ]
     ],
     "seams": [
      {
       "t": 2.8328,
       "from": 2.206,
       "to": 2.8988,
       "pause": 0.6929,
       "kind": "word"
      },
      {
       "t": 5.5728,
       "from": 5.4548,
       "to": 5.6388,
       "pause": 0.184,
       "kind": "word"
      },
      {
       "t": 8.7307,
       "from": 7.5548,
       "to": 8.7647,
       "pause": 1.2099,
       "kind": "sentence"
      },
      {
       "t": 11.3778,
       "from": 10.6807,
       "to": 11.4438,
       "pause": 0.7631,
       "kind": "word"
      },
      {
       "t": 13.3747,
       "from": 13.3747,
       "to": 13.3747,
       "pause": 0.0,
       "kind": "word"
      },
      {
       "t": 15.836,
       "from": 15.836,
       "to": 15.87,
       "pause": 0.034,
       "kind": "word"
      }
     ]
    },
    {
     "variant": "streaming-round",
     "file": "audio/en_billing_streaming-round.m4a",
     "seconds": 20.6193,
     "speech": [
      [
       0.034,
       2.942
      ],
      [
       3.1455,
       4.0375
      ],
      [
       4.6175,
       5.6375
      ],
      [
       5.7695,
       6.2775
      ],
      [
       6.6605,
       8.0325
      ],
      [
       8.1645,
       9.0245
      ],
      [
       9.3485,
       9.6645
      ],
      [
       9.8648,
       11.2368
      ],
      [
       11.6888,
       12.2928
      ],
      [
       12.5119,
       14.2679
      ],
      [
       14.3999,
       14.8608
      ],
      [
       14.8608,
       15.2108
      ],
      [
       16.0468,
       17.0348
      ],
      [
       17.4548,
       17.9723
      ],
      [
       17.9742,
       19.8902
      ]
     ],
     "seams": [
      {
       "t": 3.1115,
       "from": 2.942,
       "to": 3.1455,
       "pause": 0.2035,
       "kind": "word"
      },
      {
       "t": 6.5945,
       "from": 6.2775,
       "to": 6.6605,
       "pause": 0.383,
       "kind": "word"
      },
      {
       "t": 9.7988,
       "from": 9.6644,
       "to": 9.8648,
       "pause": 0.2004,
       "kind": "sentence"
      },
      {
       "t": 12.4459,
       "from": 12.2928,
       "to": 12.5119,
       "pause": 0.2191,
       "kind": "word"
      },
      {
       "t": 14.8608,
       "from": 14.8608,
       "to": 14.8608,
       "pause": 0.0,
       "kind": "word"
      },
      {
       "t": 17.9722,
       "from": 17.9722,
       "to": 17.9742,
       "pause": 0.002,
       "kind": "word"
      }
     ]
    }
   ]
  },
  {
   "text_id": "en_directions",
   "lang": "en",
   "seed": 1,
   "first_chunk": 0,
   "chunks": [
    "Sure, here's the easiest way to",
    "get there from the station.",
    "Take the north exit and turn left",
    "onto Main Street."
   ],
   "modes": [
    {
     "variant": "independent",
     "file": "audio/en_directions_independent.m4a",
     "seconds": 9.7988,
     "speech": [
      [
       0.066,
       0.542
      ],
      [
       0.738,
       2.206
      ],
      [
       2.6346,
       4.1666
      ],
      [
       5.0351,
       6.2151
      ],
      [
       6.3471,
       7.2711
      ],
      [
       7.743,
       9.115
      ]
     ],
     "seams": [
      {
       "t": 2.6006,
       "from": 2.2059,
       "to": 2.6346,
       "pause": 0.4287,
       "kind": "word"
      },
      {
       "t": 4.9691,
       "from": 4.1666,
       "to": 5.0351,
       "pause": 0.8684,
       "kind": "sentence"
      },
      {
       "t": 7.709,
       "from": 7.271,
       "to": 7.743,
       "pause": 0.472,
       "kind": "word"
      }
     ]
    },
    {
     "variant": "fish_history",
     "file": "audio/en_directions_fish_history.m4a",
     "seconds": 8.3127,
     "speech": [
      [
       0.066,
       0.542
      ],
      [
       0.738,
       2.206
      ],
      [
       2.6666,
       4.0386
      ],
      [
       4.4634,
       6.7954
      ],
      [
       7.0784,
       8.0664
      ]
     ],
     "seams": [
      {
       "t": 2.6006,
       "from": 2.2059,
       "to": 2.6666,
       "pause": 0.4607,
       "kind": "word"
      },
      {
       "t": 4.3654,
       "from": 4.0386,
       "to": 4.4634,
       "pause": 0.4247,
       "kind": "sentence"
      },
      {
       "t": 7.0124,
       "from": 6.7953,
       "to": 7.0784,
       "pause": 0.2831,
       "kind": "word"
      }
     ]
    },
    {
     "variant": "streaming-round-w1",
     "file": "audio/en_directions_streaming-round-w1.m4a",
     "seconds": 9.9381,
     "speech": [
      [
       0.098,
       0.51
      ],
      [
       0.674,
       2.302
      ],
      [
       3.0206,
       4.3286
      ],
      [
       5.2528,
       6.4328
      ],
      [
       6.5648,
       7.5208
      ],
      [
       8.2074,
       9.0674
      ]
     ],
     "seams": [
      {
       "t": 3.0186,
       "from": 2.302,
       "to": 3.0206,
       "pause": 0.7186,
       "kind": "word"
      },
      {
       "t": 5.1548,
       "from": 4.3286,
       "to": 5.2528,
       "pause": 0.9243,
       "kind": "sentence"
      },
      {
       "t": 8.1734,
       "from": 7.5208,
       "to": 8.2074,
       "pause": 0.6866,
       "kind": "word"
      }
     ]
    },
    {
     "variant": "streaming-round",
     "file": "audio/en_directions_streaming-round.m4a",
     "seconds": 10.449,
     "speech": [
      [
       0.002,
       0.51
      ],
      [
       0.674,
       2.334
      ],
      [
       3.0526,
       4.3606
      ],
      [
       5.6243,
       6.8043
      ],
      [
       7.0323,
       8.1483
      ],
      [
       8.2683,
       9.2563
      ]
     ],
     "seams": [
      {
       "t": 3.0186,
       "from": 2.334,
       "to": 3.0526,
       "pause": 0.7186,
       "kind": "word"
      },
      {
       "t": 5.5263,
       "from": 4.3605,
       "to": 5.6243,
       "pause": 1.2638,
       "kind": "sentence"
      },
      {
       "t": 8.2663,
       "from": 8.1483,
       "to": 8.2683,
       "pause": 0.12,
       "kind": "word"
      }
     ]
    }
   ]
  },
  {
   "text_id": "zh_trip",
   "lang": "zh",
   "seed": 1,
   "first_chunk": 0,
   "chunks": [
    "好的，我来帮您安排一下明天的行程。",
    "早上吃完早饭，先打车去博物馆，",
    "路上不堵的话，刚好赶上开门。"
   ],
   "modes": [
    {
     "variant": "independent",
     "file": "audio/zh_trip_independent.m4a",
     "seconds": 10.5883,
     "speech": [
      [
       0.098,
       0.446
      ],
      [
       0.61,
       2.59
      ],
      [
       3.131,
       4.471
      ],
      [
       4.859,
       6.391
      ],
      [
       7.4964,
       8.7084
      ],
      [
       8.9684,
       10.1804
      ]
     ],
     "seams": [
      {
       "t": 3.065,
       "from": 2.59,
       "to": 3.131,
       "pause": 0.5411,
       "kind": "sentence"
      },
      {
       "t": 7.4304,
       "from": 6.391,
       "to": 7.4964,
       "pause": 1.1054,
       "kind": "clause"
      }
     ]
    },
    {
     "variant": "fish_history",
     "file": "audio/zh_trip_fish_history.m4a",
     "seconds": 9.6131,
     "speech": [
      [
       0.098,
       0.446
      ],
      [
       0.61,
       2.59
      ],
      [
       3.099,
       4.311
      ],
      [
       4.539,
       5.911
      ],
      [
       6.7998,
       7.8838
      ],
      [
       8.1118,
       9.2278
      ]
     ],
     "seams": [
      {
       "t": 3.065,
       "from": 2.59,
       "to": 3.099,
       "pause": 0.5091,
       "kind": "sentence"
      },
      {
       "t": 6.7338,
       "from": 5.911,
       "to": 6.7998,
       "pause": 0.8888,
       "kind": "clause"
      }
     ]
    },
    {
     "variant": "streaming-round-w1",
     "file": "audio/zh_trip_streaming-round-w1.m4a",
     "seconds": 10.8669,
     "speech": [
      [
       0.034,
       0.414
      ],
      [
       0.866,
       2.846
      ],
      [
       3.935,
       5.115
      ],
      [
       5.279,
       6.555
      ],
      [
       7.3571,
       8.4731
      ],
      [
       8.6691,
       9.8811
      ]
     ],
     "seams": [
      {
       "t": 3.901,
       "from": 2.846,
       "to": 3.935,
       "pause": 1.089,
       "kind": "sentence"
      },
      {
       "t": 7.2911,
       "from": 6.5549,
       "to": 7.3571,
       "pause": 0.8021,
       "kind": "clause"
      }
     ]
    },
    {
     "variant": "streaming-round",
     "file": "audio/zh_trip_streaming-round.m4a",
     "seconds": 10.4025,
     "speech": [
      [
       0.034,
       0.414
      ],
      [
       1.026,
       2.942
      ],
      [
       3.8276,
       4.9756
      ],
      [
       5.1396,
       6.5116
      ],
      [
       7.2322,
       8.2522
      ],
      [
       8.4162,
       9.5002
      ]
     ],
     "seams": [
      {
       "t": 3.7616,
       "from": 2.9419,
       "to": 3.8276,
       "pause": 0.8857,
       "kind": "sentence"
      },
      {
       "t": 7.1982,
       "from": 6.5116,
       "to": 7.2322,
       "pause": 0.7206,
       "kind": "clause"
      }
     ]
    }
   ]
  }
 ]
};
