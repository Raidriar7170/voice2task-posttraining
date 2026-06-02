# Use TRL and PEFT as the primary first-phase training stack

Voice2Task Post-Training will use the Hugging Face Transformers, PEFT, and TRL path as the first transparent SFT/DPO implementation, with Qwen-family small instruction models as reference targets. ms-swift may be added as an engineering route for larger A100 runs, but it should not be the only implementation path for the first phase.
