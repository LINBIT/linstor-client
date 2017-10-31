diskoptions="""<command name="disk-options">
	<summary>Change the disk options of an attached lower-level device.</summary>
	<argument>minor</argument>
	<option name="set-defaults" type="flag">
	</option>
	<option name="on-io-error" type="handler">
		<handler>pass_on</handler>
		<handler>call-local-io-error</handler>
		<handler>detach</handler>
	</option>
	<option name="disk-barrier" type="boolean">
		<default>no</default>
	</option>
	<option name="disk-flushes" type="boolean">
		<default>yes</default>
	</option>
	<option name="disk-drain" type="boolean">
		<default>yes</default>
	</option>
	<option name="md-flushes" type="boolean">
		<default>yes</default>
	</option>
	<option name="resync-after" type="numeric">
		<min>-1</min>
		<max>1048575</max>
		<default>-1</default>
		<unit_prefix>1</unit_prefix>
	</option>
	<option name="al-extents" type="numeric">
		<min>67</min>
		<max>65534</max>
		<default>1237</default>
		<unit_prefix>1</unit_prefix>
	</option>
	<option name="al-updates" type="boolean">
		<default>yes</default>
	</option>
	<option name="discard-zeroes-if-aligned" type="boolean">
		<default>yes</default>
	</option>
	<option name="disable-write-same" type="boolean">
		<default>no</default>
	</option>
	<option name="disk-timeout" type="numeric">
		<min>0</min>
		<max>6000</max>
		<default>0</default>
		<unit_prefix>1</unit_prefix>
		<unit>1/10 seconds</unit>
	</option>
	<option name="read-balancing" type="handler">
		<handler>prefer-local</handler>
		<handler>prefer-remote</handler>
		<handler>round-robin</handler>
		<handler>least-pending</handler>
		<handler>when-congested-remote</handler>
		<handler>32K-striping</handler>
		<handler>64K-striping</handler>
		<handler>128K-striping</handler>
		<handler>256K-striping</handler>
		<handler>512K-striping</handler>
		<handler>1M-striping</handler>
	</option>
	<option name="rs-discard-granularity" type="numeric">
		<min>0</min>
		<max>1048576</max>
		<default>0</default>
		<unit_prefix>1</unit_prefix>
		<unit>bytes</unit>
	</option>
</command>"""
netoptions="""<command name="new-peer">
	<summary>Make a peer host known to a resource.</summary>
	<argument>resource</argument>
	<argument>peer_node_id</argument>
	<option name="transport" type="string">
	</option>
	<option name="protocol" type="handler">
		<handler>A</handler>
		<handler>B</handler>
		<handler>C</handler>
	</option>
	<option name="timeout" type="numeric">
		<min>1</min>
		<max>600</max>
		<default>60</default>
		<unit_prefix>1</unit_prefix>
		<unit>1/10 seconds</unit>
	</option>
	<option name="max-epoch-size" type="numeric">
		<min>1</min>
		<max>20000</max>
		<default>2048</default>
		<unit_prefix>1</unit_prefix>
	</option>
	<option name="connect-int" type="numeric">
		<min>1</min>
		<max>120</max>
		<default>10</default>
		<unit_prefix>1</unit_prefix>
		<unit>seconds</unit>
	</option>
	<option name="ping-int" type="numeric">
		<min>1</min>
		<max>120</max>
		<default>10</default>
		<unit_prefix>1</unit_prefix>
		<unit>seconds</unit>
	</option>
	<option name="sndbuf-size" type="numeric">
		<min>0</min>
		<max>10485760</max>
		<default>0</default>
		<unit_prefix>1</unit_prefix>
		<unit>bytes</unit>
	</option>
	<option name="rcvbuf-size" type="numeric">
		<min>0</min>
		<max>10485760</max>
		<default>0</default>
		<unit_prefix>1</unit_prefix>
		<unit>bytes</unit>
	</option>
	<option name="ko-count" type="numeric">
		<min>0</min>
		<max>200</max>
		<default>7</default>
		<unit_prefix>1</unit_prefix>
	</option>
	<option name="allow-two-primaries" type="boolean">
		<default>no</default>
	</option>
	<option name="cram-hmac-alg" type="string">
	</option>
	<option name="shared-secret" type="string">
	</option>
	<option name="after-sb-0pri" type="handler">
		<handler>disconnect</handler>
		<handler>discard-younger-primary</handler>
		<handler>discard-older-primary</handler>
		<handler>discard-zero-changes</handler>
		<handler>discard-least-changes</handler>
		<handler>discard-local</handler>
		<handler>discard-remote</handler>
	</option>
	<option name="after-sb-1pri" type="handler">
		<handler>disconnect</handler>
		<handler>consensus</handler>
		<handler>discard-secondary</handler>
		<handler>call-pri-lost-after-sb</handler>
		<handler>violently-as0p</handler>
	</option>
	<option name="after-sb-2pri" type="handler">
		<handler>disconnect</handler>
		<handler>call-pri-lost-after-sb</handler>
		<handler>violently-as0p</handler>
	</option>
	<option name="always-asbp" type="boolean">
		<default>no</default>
	</option>
	<option name="rr-conflict" type="handler">
		<handler>disconnect</handler>
		<handler>call-pri-lost</handler>
		<handler>violently</handler>
	</option>
	<option name="ping-timeout" type="numeric">
		<min>1</min>
		<max>300</max>
		<default>5</default>
		<unit_prefix>1</unit_prefix>
		<unit>1/10 seconds</unit>
	</option>
	<option name="data-integrity-alg" type="string">
	</option>
	<option name="tcp-cork" type="boolean">
		<default>yes</default>
	</option>
	<option name="on-congestion" type="handler">
		<handler>block</handler>
		<handler>pull-ahead</handler>
		<handler>disconnect</handler>
	</option>
	<option name="congestion-fill" type="numeric">
		<min>0</min>
		<max>20971520</max>
		<default>0</default>
		<unit_prefix>s</unit_prefix>
		<unit>bytes</unit>
	</option>
	<option name="congestion-extents" type="numeric">
		<min>67</min>
		<max>65534</max>
		<default>1237</default>
		<unit_prefix>1</unit_prefix>
	</option>
	<option name="csums-alg" type="string">
	</option>
	<option name="csums-after-crash-only" type="boolean">
		<default>no</default>
	</option>
	<option name="verify-alg" type="string">
	</option>
	<option name="use-rle" type="boolean">
		<default>yes</default>
	</option>
	<option name="socket-check-timeout" type="numeric">
		<min>0</min>
		<max>300</max>
		<default>0</default>
		<unit_prefix>1</unit_prefix>
	</option>
	<option name="fencing" type="handler">
		<handler>dont-care</handler>
		<handler>resource-only</handler>
		<handler>resource-and-stonith</handler>
	</option>
	<option name="max-buffers" type="numeric">
		<min>32</min>
		<max>131072</max>
		<default>2048</default>
		<unit_prefix>1</unit_prefix>
	</option>
	<option name="_name" type="string">
	</option>
</command>"""
peerdeviceoptions="""<command name="peer-device-options">
	<summary>Change peer-device options.</summary>
	<argument>resource</argument>
	<argument>peer_node_id</argument>
	<argument>volume</argument>
	<option name="set-defaults" type="flag">
	</option>
	<option name="resync-rate" type="numeric">
		<min>1</min>
		<max>4194304</max>
		<default>250</default>
		<unit_prefix>k</unit_prefix>
		<unit>bytes/second</unit>
	</option>
	<option name="c-plan-ahead" type="numeric">
		<min>0</min>
		<max>300</max>
		<default>20</default>
		<unit_prefix>1</unit_prefix>
		<unit>1/10 seconds</unit>
	</option>
	<option name="c-delay-target" type="numeric">
		<min>1</min>
		<max>100</max>
		<default>10</default>
		<unit_prefix>1</unit_prefix>
		<unit>1/10 seconds</unit>
	</option>
	<option name="c-fill-target" type="numeric">
		<min>0</min>
		<max>1048576</max>
		<default>100</default>
		<unit_prefix>s</unit_prefix>
		<unit>bytes</unit>
	</option>
	<option name="c-max-rate" type="numeric">
		<min>250</min>
		<max>4194304</max>
		<default>102400</default>
		<unit_prefix>k</unit_prefix>
		<unit>bytes/second</unit>
	</option>
	<option name="c-min-rate" type="numeric">
		<min>0</min>
		<max>4194304</max>
		<default>250</default>
		<unit_prefix>k</unit_prefix>
		<unit>bytes/second</unit>
	</option>
	<option name="bitmap" type="boolean">
		<default>yes</default>
	</option>
</command>"""
resourceoptions="""<command name="resource-options">
	<summary>Change the resource options of an existing resource.</summary>
	<argument>resource</argument>
	<option name="set-defaults" type="flag">
	</option>
	<option name="cpu-mask" type="string">
	</option>
	<option name="on-no-data-accessible" type="handler">
		<handler>io-error</handler>
		<handler>suspend-io</handler>
	</option>
	<option name="auto-promote" type="boolean">
		<default>yes</default>
	</option>
	<option name="peer-ack-window" type="numeric">
		<min>2048</min>
		<max>204800</max>
		<default>4096</default>
		<unit_prefix>s</unit_prefix>
		<unit>bytes</unit>
	</option>
	<option name="peer-ack-delay" type="numeric">
		<min>1</min>
		<max>10000</max>
		<default>100</default>
		<unit_prefix>1</unit_prefix>
		<unit>milliseconds</unit>
	</option>
	<option name="twopc-timeout" type="numeric">
		<min>50</min>
		<max>600</max>
		<default>300</default>
		<unit_prefix>1</unit_prefix>
		<unit>1/10 seconds</unit>
	</option>
	<option name="twopc-retry-timeout" type="numeric">
		<min>1</min>
		<max>50</max>
		<default>1</default>
		<unit_prefix>1</unit_prefix>
		<unit>1/10 seconds</unit>
	</option>
	<option name="auto-promote-timeout" type="numeric">
		<min>0</min>
		<max>600</max>
		<default>20</default>
		<unit_prefix>1</unit_prefix>
		<unit>1/10 seconds</unit>
	</option>
	<option name="max-io-depth" type="numeric">
		<min>4</min>
		<max>4294967295</max>
		<default>8000</default>
		<unit_prefix>1</unit_prefix>
	</option>
	<option name="quorum" type="numeric-or-symbol">
		<min>1</min>
		<max>32</max>
		<default>off</default>
		<symbol>off</symbol>
		<symbol>majority</symbol>
		<symbol>all</symbol>
	</option>
	<option name="on-no-quorum" type="handler">
		<handler>io-error</handler>
		<handler>suspend-io</handler>
	</option>
</command>"""
