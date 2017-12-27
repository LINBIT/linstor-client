"""
Do not edit, this file is generated.

Json representation for viewing:
{
  "peer-ack-delay": {
    "category": "resource-options", 
    "unit_prefix": "1", 
    "min": 1, 
    "default": 100, 
    "max": 10000, 
    "type": "numeric", 
    "unit": "milliseconds"
  }, 
  "max-epoch-size": {
    "category": "net-options", 
    "unit_prefix": "1", 
    "min": 1, 
    "default": 2048, 
    "max": 20000, 
    "type": "numeric"
  }, 
  "csums-alg": {
    "category": "net-options", 
    "type": "string"
  }, 
  "auto-promote-timeout": {
    "category": "resource-options", 
    "unit_prefix": "1", 
    "min": 0, 
    "default": 20, 
    "max": 600, 
    "type": "numeric", 
    "unit": "1/10 seconds"
  }, 
  "help": "Change the network options of a connection.", 
  "c-fill-target": {
    "category": "peer-device-options", 
    "unit_prefix": "s", 
    "min": 0, 
    "default": 100, 
    "max": 1048576, 
    "type": "numeric", 
    "unit": "bytes"
  }, 
  "disable-write-same": {
    "category": "disk-options", 
    "default": false, 
    "type": "boolean"
  }, 
  "on-no-data-accessible": {
    "category": "resource-options", 
    "type": "handler", 
    "handlers": [
      "io-error", 
      "suspend-io"
    ]
  }, 
  "resync-after": {
    "category": "disk-options", 
    "unit_prefix": "1", 
    "min": -1, 
    "default": -1, 
    "max": 1048575, 
    "type": "numeric"
  }, 
  "bitmap": {
    "category": "peer-device-options", 
    "default": true, 
    "type": "boolean"
  }, 
  "on-no-quorum": {
    "category": "resource-options", 
    "type": "handler", 
    "handlers": [
      "io-error", 
      "suspend-io"
    ]
  }, 
  "twopc-retry-timeout": {
    "category": "resource-options", 
    "unit_prefix": "1", 
    "min": 1, 
    "default": 1, 
    "max": 50, 
    "type": "numeric", 
    "unit": "1/10 seconds"
  }, 
  "after-sb-0pri": {
    "category": "net-options", 
    "type": "handler", 
    "handlers": [
      "disconnect", 
      "discard-younger-primary", 
      "discard-older-primary", 
      "discard-zero-changes", 
      "discard-least-changes", 
      "discard-local", 
      "discard-remote"
    ]
  }, 
  "ko-count": {
    "category": "net-options", 
    "unit_prefix": "1", 
    "min": 0, 
    "default": 7, 
    "max": 200, 
    "type": "numeric"
  }, 
  "c-min-rate": {
    "category": "peer-device-options", 
    "unit_prefix": "k", 
    "min": 0, 
    "default": 250, 
    "max": 4194304, 
    "type": "numeric", 
    "unit": "bytes/second"
  }, 
  "data-integrity-alg": {
    "category": "net-options", 
    "type": "string"
  }, 
  "al-updates": {
    "category": "disk-options", 
    "default": true, 
    "type": "boolean"
  }, 
  "protocol": {
    "category": "net-options", 
    "type": "handler", 
    "handlers": [
      "A", 
      "B", 
      "C"
    ]
  }, 
  "ping-timeout": {
    "category": "net-options", 
    "unit_prefix": "1", 
    "min": 1, 
    "default": 5, 
    "max": 300, 
    "type": "numeric", 
    "unit": "1/10 seconds"
  }, 
  "c-delay-target": {
    "category": "peer-device-options", 
    "unit_prefix": "1", 
    "min": 1, 
    "default": 10, 
    "max": 100, 
    "type": "numeric", 
    "unit": "1/10 seconds"
  }, 
  "sndbuf-size": {
    "category": "net-options", 
    "unit_prefix": "1", 
    "min": 0, 
    "default": 0, 
    "max": 10485760, 
    "type": "numeric", 
    "unit": "bytes"
  }, 
  "discard-zeroes-if-aligned": {
    "category": "disk-options", 
    "default": true, 
    "type": "boolean"
  }, 
  "timeout": {
    "category": "net-options", 
    "unit_prefix": "1", 
    "min": 1, 
    "default": 60, 
    "max": 600, 
    "type": "numeric", 
    "unit": "1/10 seconds"
  }, 
  "rcvbuf-size": {
    "category": "net-options", 
    "unit_prefix": "1", 
    "min": 0, 
    "default": 0, 
    "max": 10485760, 
    "type": "numeric", 
    "unit": "bytes"
  }, 
  "max-buffers": {
    "category": "net-options", 
    "unit_prefix": "1", 
    "min": 32, 
    "default": 2048, 
    "max": 131072, 
    "type": "numeric"
  }, 
  "disk-drain": {
    "category": "disk-options", 
    "default": true, 
    "type": "boolean"
  }, 
  "resync-rate": {
    "category": "peer-device-options", 
    "unit_prefix": "k", 
    "min": 1, 
    "default": 250, 
    "max": 4194304, 
    "type": "numeric", 
    "unit": "bytes/second"
  }, 
  "max-io-depth": {
    "category": "resource-options", 
    "unit_prefix": "1", 
    "min": 4, 
    "default": 8000, 
    "max": 4294967295, 
    "type": "numeric"
  }, 
  "always-asbp": {
    "category": "net-options", 
    "default": false, 
    "type": "boolean"
  }, 
  "twopc-timeout": {
    "category": "resource-options", 
    "unit_prefix": "1", 
    "min": 50, 
    "default": 300, 
    "max": 600, 
    "type": "numeric", 
    "unit": "1/10 seconds"
  }, 
  "congestion-extents": {
    "category": "net-options", 
    "unit_prefix": "1", 
    "min": 67, 
    "default": 1237, 
    "max": 65534, 
    "type": "numeric"
  }, 
  "on-congestion": {
    "category": "net-options", 
    "type": "handler", 
    "handlers": [
      "block", 
      "pull-ahead", 
      "disconnect"
    ]
  }, 
  "congestion-fill": {
    "category": "net-options", 
    "unit_prefix": "s", 
    "min": 0, 
    "default": 0, 
    "max": 20971520, 
    "type": "numeric", 
    "unit": "bytes"
  }, 
  "ping-int": {
    "category": "net-options", 
    "unit_prefix": "1", 
    "min": 1, 
    "default": 10, 
    "max": 120, 
    "type": "numeric", 
    "unit": "seconds"
  }, 
  "disk-barrier": {
    "category": "disk-options", 
    "default": false, 
    "type": "boolean"
  }, 
  "read-balancing": {
    "category": "disk-options", 
    "type": "handler", 
    "handlers": [
      "prefer-local", 
      "prefer-remote", 
      "round-robin", 
      "least-pending", 
      "when-congested-remote", 
      "32K-striping", 
      "64K-striping", 
      "128K-striping", 
      "256K-striping", 
      "512K-striping", 
      "1M-striping"
    ]
  }, 
  "cpu-mask": {
    "category": "resource-options", 
    "type": "string"
  }, 
  "on-io-error": {
    "category": "disk-options", 
    "type": "handler", 
    "handlers": [
      "pass_on", 
      "call-local-io-error", 
      "detach"
    ]
  }, 
  "c-max-rate": {
    "category": "peer-device-options", 
    "unit_prefix": "k", 
    "min": 250, 
    "default": 102400, 
    "max": 4194304, 
    "type": "numeric", 
    "unit": "bytes/second"
  }, 
  "rr-conflict": {
    "category": "net-options", 
    "type": "handler", 
    "handlers": [
      "disconnect", 
      "call-pri-lost", 
      "violently"
    ]
  }, 
  "al-extents": {
    "category": "disk-options", 
    "unit_prefix": "1", 
    "min": 67, 
    "default": 1237, 
    "max": 65534, 
    "type": "numeric"
  }, 
  "auto-promote": {
    "category": "resource-options", 
    "default": true, 
    "type": "boolean"
  }, 
  "connect-int": {
    "category": "net-options", 
    "unit_prefix": "1", 
    "min": 1, 
    "default": 10, 
    "max": 120, 
    "type": "numeric", 
    "unit": "seconds"
  }, 
  "tcp-cork": {
    "category": "net-options", 
    "default": true, 
    "type": "boolean"
  }, 
  "use-rle": {
    "category": "net-options", 
    "default": true, 
    "type": "boolean"
  }, 
  "_name": {
    "category": "net-options", 
    "type": "string"
  }, 
  "fencing": {
    "category": "net-options", 
    "type": "handler", 
    "handlers": [
      "dont-care", 
      "resource-only", 
      "resource-and-stonith"
    ]
  }, 
  "csums-after-crash-only": {
    "category": "net-options", 
    "default": false, 
    "type": "boolean"
  }, 
  "socket-check-timeout": {
    "category": "net-options", 
    "unit_prefix": "1", 
    "min": 0, 
    "default": 0, 
    "max": 300, 
    "type": "numeric"
  }, 
  "md-flushes": {
    "category": "disk-options", 
    "default": true, 
    "type": "boolean"
  }, 
  "peer-ack-window": {
    "category": "resource-options", 
    "unit_prefix": "s", 
    "min": 2048, 
    "default": 4096, 
    "max": 204800, 
    "type": "numeric", 
    "unit": "bytes"
  }, 
  "cram-hmac-alg": {
    "category": "net-options", 
    "type": "string"
  }, 
  "verify-alg": {
    "category": "net-options", 
    "type": "string"
  }, 
  "allow-two-primaries": {
    "category": "net-options", 
    "default": false, 
    "type": "boolean"
  }, 
  "quorum": {
    "category": "resource-options", 
    "type": "numeric-or-symbol"
  }, 
  "shared-secret": {
    "category": "net-options", 
    "type": "string"
  }, 
  "disk-timeout": {
    "category": "disk-options", 
    "unit_prefix": "1", 
    "min": 0, 
    "default": 0, 
    "max": 6000, 
    "type": "numeric", 
    "unit": "1/10 seconds"
  }, 
  "set-defaults": {
    "category": "net-options", 
    "type": "flag"
  }, 
  "rs-discard-granularity": {
    "category": "disk-options", 
    "unit_prefix": "1", 
    "min": 0, 
    "default": 0, 
    "max": 1048576, 
    "type": "numeric", 
    "unit": "bytes"
  }, 
  "disk-flushes": {
    "category": "disk-options", 
    "default": true, 
    "type": "boolean"
  }, 
  "after-sb-2pri": {
    "category": "net-options", 
    "type": "handler", 
    "handlers": [
      "disconnect", 
      "call-pri-lost-after-sb", 
      "violently-as0p"
    ]
  }, 
  "after-sb-1pri": {
    "category": "net-options", 
    "type": "handler", 
    "handlers": [
      "disconnect", 
      "consensus", 
      "discard-secondary", 
      "call-pri-lost-after-sb", 
      "violently-as0p"
    ]
  }, 
  "c-plan-ahead": {
    "category": "peer-device-options", 
    "unit_prefix": "1", 
    "min": 0, 
    "default": 20, 
    "max": 300, 
    "type": "numeric", 
    "unit": "1/10 seconds"
  }
}
"""

drbdoptions_raw = """(dp0
S'peer-ack-delay'
p1
(dp2
S'category'
p3
S'resource-options'
p4
sS'unit_prefix'
p5
S'1'
p6
sS'min'
p7
I1
sS'default'
p8
I100
sS'max'
p9
I10000
sS'type'
p10
S'numeric'
p11
sS'unit'
p12
S'milliseconds'
p13
ssS'max-epoch-size'
p14
(dp15
g3
S'net-options'
p16
sg5
S'1'
p17
sg7
I1
sg8
I2048
sg9
I20000
sg10
S'numeric'
p18
ssS'csums-alg'
p19
(dp20
g3
g16
sg10
S'string'
p21
ssS'auto-promote-timeout'
p22
(dp23
g3
g4
sg5
S'1'
p24
sg7
I0
sg8
I20
sg9
I600
sg10
S'numeric'
p25
sg12
S'1/10 seconds'
p26
ssS'help'
p27
S'Change the network options of a connection.'
p28
sS'c-fill-target'
p29
(dp30
g3
S'peer-device-options'
p31
sg5
S's'
p32
sg7
I0
sg8
I100
sg9
I1048576
sg10
S'numeric'
p33
sg12
S'bytes'
p34
ssS'disable-write-same'
p35
(dp36
g3
S'disk-options'
p37
sg8
I00
sg10
S'boolean'
p38
ssS'on-no-data-accessible'
p39
(dp40
g3
g4
sg10
S'handler'
p41
sS'handlers'
p42
(lp43
S'io-error'
p44
aS'suspend-io'
p45
assS'resync-after'
p46
(dp47
g3
g37
sg5
S'1'
p48
sg7
I-1
sg8
I-1
sg9
I1048575
sg10
S'numeric'
p49
ssS'bitmap'
p50
(dp51
g3
g31
sg8
I01
sg10
S'boolean'
p52
ssS'on-no-quorum'
p53
(dp54
g3
g4
sg10
S'handler'
p55
sg42
(lp56
S'io-error'
p57
aS'suspend-io'
p58
assS'twopc-retry-timeout'
p59
(dp60
g3
g4
sg5
S'1'
p61
sg7
I1
sg8
I1
sg9
I50
sg10
S'numeric'
p62
sg12
S'1/10 seconds'
p63
ssS'after-sb-0pri'
p64
(dp65
g3
g16
sg10
S'handler'
p66
sg42
(lp67
S'disconnect'
p68
aS'discard-younger-primary'
p69
aS'discard-older-primary'
p70
aS'discard-zero-changes'
p71
aS'discard-least-changes'
p72
aS'discard-local'
p73
aS'discard-remote'
p74
assS'ko-count'
p75
(dp76
g3
g16
sg5
S'1'
p77
sg7
I0
sg8
I7
sg9
I200
sg10
S'numeric'
p78
ssS'c-min-rate'
p79
(dp80
g3
g31
sg5
S'k'
p81
sg7
I0
sg8
I250
sg9
I4194304
sg10
S'numeric'
p82
sg12
S'bytes/second'
p83
ssS'data-integrity-alg'
p84
(dp85
g3
g16
sg10
S'string'
p86
ssS'al-updates'
p87
(dp88
g3
g37
sg8
I01
sg10
S'boolean'
p89
ssS'protocol'
p90
(dp91
g3
g16
sg10
S'handler'
p92
sg42
(lp93
S'A'
p94
aS'B'
p95
aS'C'
p96
assS'ping-timeout'
p97
(dp98
g3
g16
sg5
S'1'
p99
sg7
I1
sg8
I5
sg9
I300
sg10
S'numeric'
p100
sg12
S'1/10 seconds'
p101
ssS'c-delay-target'
p102
(dp103
g3
g31
sg5
S'1'
p104
sg7
I1
sg8
I10
sg9
I100
sg10
S'numeric'
p105
sg12
S'1/10 seconds'
p106
ssS'sndbuf-size'
p107
(dp108
g3
g16
sg5
S'1'
p109
sg7
I0
sg8
I0
sg9
I10485760
sg10
S'numeric'
p110
sg12
S'bytes'
p111
ssS'discard-zeroes-if-aligned'
p112
(dp113
g3
g37
sg8
I01
sg10
S'boolean'
p114
ssS'timeout'
p115
(dp116
g3
g16
sg5
S'1'
p117
sg7
I1
sg8
I60
sg9
I600
sg10
S'numeric'
p118
sg12
S'1/10 seconds'
p119
ssS'rcvbuf-size'
p120
(dp121
g3
g16
sg5
S'1'
p122
sg7
I0
sg8
I0
sg9
I10485760
sg10
S'numeric'
p123
sg12
S'bytes'
p124
ssS'max-buffers'
p125
(dp126
g3
g16
sg5
S'1'
p127
sg7
I32
sg8
I2048
sg9
I131072
sg10
S'numeric'
p128
ssS'disk-drain'
p129
(dp130
g3
g37
sg8
I01
sg10
S'boolean'
p131
ssS'resync-rate'
p132
(dp133
g3
g31
sg5
S'k'
p134
sg7
I1
sg8
I250
sg9
I4194304
sg10
S'numeric'
p135
sg12
S'bytes/second'
p136
ssS'max-io-depth'
p137
(dp138
g3
g4
sg5
S'1'
p139
sg7
I4
sg8
I8000
sg9
I4294967295
sg10
S'numeric'
p140
ssS'always-asbp'
p141
(dp142
g3
g16
sg8
I00
sg10
S'boolean'
p143
ssS'twopc-timeout'
p144
(dp145
g3
g4
sg5
S'1'
p146
sg7
I50
sg8
I300
sg9
I600
sg10
S'numeric'
p147
sg12
S'1/10 seconds'
p148
ssS'congestion-extents'
p149
(dp150
g3
g16
sg5
S'1'
p151
sg7
I67
sg8
I1237
sg9
I65534
sg10
S'numeric'
p152
ssS'on-congestion'
p153
(dp154
g3
g16
sg10
S'handler'
p155
sg42
(lp156
S'block'
p157
aS'pull-ahead'
p158
aS'disconnect'
p159
assS'congestion-fill'
p160
(dp161
g3
g16
sg5
S's'
p162
sg7
I0
sg8
I0
sg9
I20971520
sg10
S'numeric'
p163
sg12
S'bytes'
p164
ssS'ping-int'
p165
(dp166
g3
g16
sg5
S'1'
p167
sg7
I1
sg8
I10
sg9
I120
sg10
S'numeric'
p168
sg12
S'seconds'
p169
ssS'disk-barrier'
p170
(dp171
g3
g37
sg8
I00
sg10
S'boolean'
p172
ssS'read-balancing'
p173
(dp174
g3
g37
sg10
S'handler'
p175
sg42
(lp176
S'prefer-local'
p177
aS'prefer-remote'
p178
aS'round-robin'
p179
aS'least-pending'
p180
aS'when-congested-remote'
p181
aS'32K-striping'
p182
aS'64K-striping'
p183
aS'128K-striping'
p184
aS'256K-striping'
p185
aS'512K-striping'
p186
aS'1M-striping'
p187
assS'cpu-mask'
p188
(dp189
g3
g4
sg10
S'string'
p190
ssS'on-io-error'
p191
(dp192
g3
g37
sg10
S'handler'
p193
sg42
(lp194
S'pass_on'
p195
aS'call-local-io-error'
p196
aS'detach'
p197
assS'c-max-rate'
p198
(dp199
g3
g31
sg5
S'k'
p200
sg7
I250
sg8
I102400
sg9
I4194304
sg10
S'numeric'
p201
sg12
S'bytes/second'
p202
ssS'rr-conflict'
p203
(dp204
g3
g16
sg10
S'handler'
p205
sg42
(lp206
S'disconnect'
p207
aS'call-pri-lost'
p208
aS'violently'
p209
assS'al-extents'
p210
(dp211
g3
g37
sg5
S'1'
p212
sg7
I67
sg8
I1237
sg9
I65534
sg10
S'numeric'
p213
ssS'auto-promote'
p214
(dp215
g3
g4
sg8
I01
sg10
S'boolean'
p216
ssS'connect-int'
p217
(dp218
g3
g16
sg5
S'1'
p219
sg7
I1
sg8
I10
sg9
I120
sg10
S'numeric'
p220
sg12
S'seconds'
p221
ssS'tcp-cork'
p222
(dp223
g3
g16
sg8
I01
sg10
S'boolean'
p224
ssS'use-rle'
p225
(dp226
g3
g16
sg8
I01
sg10
S'boolean'
p227
ssS'_name'
p228
(dp229
g3
g16
sg10
S'string'
p230
ssS'fencing'
p231
(dp232
g3
g16
sg10
S'handler'
p233
sg42
(lp234
S'dont-care'
p235
aS'resource-only'
p236
aS'resource-and-stonith'
p237
assS'csums-after-crash-only'
p238
(dp239
g3
g16
sg8
I00
sg10
S'boolean'
p240
ssS'socket-check-timeout'
p241
(dp242
g3
g16
sg5
S'1'
p243
sg7
I0
sg8
I0
sg9
I300
sg10
S'numeric'
p244
ssS'md-flushes'
p245
(dp246
g3
g37
sg8
I01
sg10
S'boolean'
p247
ssS'peer-ack-window'
p248
(dp249
g3
g4
sg5
S's'
p250
sg7
I2048
sg8
I4096
sg9
I204800
sg10
S'numeric'
p251
sg12
S'bytes'
p252
ssS'cram-hmac-alg'
p253
(dp254
g3
g16
sg10
S'string'
p255
ssS'verify-alg'
p256
(dp257
g3
g16
sg10
S'string'
p258
ssS'allow-two-primaries'
p259
(dp260
g3
g16
sg8
I00
sg10
S'boolean'
p261
ssS'quorum'
p262
(dp263
g3
g4
sg10
S'numeric-or-symbol'
p264
ssS'shared-secret'
p265
(dp266
g3
g16
sg10
S'string'
p267
ssS'disk-timeout'
p268
(dp269
g3
g37
sg5
S'1'
p270
sg7
I0
sg8
I0
sg9
I6000
sg10
S'numeric'
p271
sg12
S'1/10 seconds'
p272
ssS'set-defaults'
p273
(dp274
g3
g16
sg10
S'flag'
p275
ssS'rs-discard-granularity'
p276
(dp277
g3
g37
sg5
S'1'
p278
sg7
I0
sg8
I0
sg9
I1048576
sg10
S'numeric'
p279
sg12
S'bytes'
p280
ssS'disk-flushes'
p281
(dp282
g3
g37
sg8
I01
sg10
S'boolean'
p283
ssS'after-sb-2pri'
p284
(dp285
g3
g16
sg10
S'handler'
p286
sg42
(lp287
S'disconnect'
p288
aS'call-pri-lost-after-sb'
p289
aS'violently-as0p'
p290
assS'after-sb-1pri'
p291
(dp292
g3
g16
sg10
S'handler'
p293
sg42
(lp294
S'disconnect'
p295
aS'consensus'
p296
aS'discard-secondary'
p297
aS'call-pri-lost-after-sb'
p298
aS'violently-as0p'
p299
assS'c-plan-ahead'
p300
(dp301
g3
g31
sg5
S'1'
p302
sg7
I0
sg8
I20
sg9
I300
sg10
S'numeric'
p303
sg12
S'1/10 seconds'
p304
ss."""