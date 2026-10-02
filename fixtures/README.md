# Fixed native inputs

These are the missing native inputs required in addition to the saved-result audit archive. The pickle payloads are unchanged research-generated files; they contain native implementation classes and require the pinned native environment. Load only the bundled, hash-checked pickle files.

`manifest.json` inventories every packaged fixture. The two controlled pickles and two checker pickles contain no server paths, contributor names, email addresses or personal URLs in their serialized string opcodes. Their bytes were retained, so their numerical states and original hashes are unchanged.

The reconstructed map is distributed as a deterministic gzip with an empty header filename and timestamp zero. Its uncompressed bytes are exactly the map used in the archived checker experiment. `map/map_manifest.json` records both hashes and sizes. The native launcher extracts it into an ignored local cache and verifies it before use.

The OpenDRIVE geometry is from CARLA Town01; upstream attribution and terms are in the repository's third-party notices. These fixtures do not recreate a complete CARLA simulator state. No simulator server or GPU is used by the controlled/checker commands.
