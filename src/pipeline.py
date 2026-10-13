"""Teacher-review pipeline: clean bundled real CSVs and verify frozen-gallery parity.

This entry point does not recollect sources, create synthetic observations or
silently overwrite the model served by Streamlit. Historical full training
entry points remain under scripts/ and are documented in the review guide.
"""
from src.preprocessing.prepare_datasets import main

if __name__ == '__main__':
    main()
