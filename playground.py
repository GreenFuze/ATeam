import llm

print("Models:")

def get_all_option_fields(options_cls):
    fields = {}
    for cls in options_cls.__mro__:
        if hasattr(cls, "__annotations__"):
            fields.update(cls.__annotations__)
    return fields

models = llm.get_models()
for model in models:
    print(f'Name: {str(model)}')
    # print(f"Options: {get_all_option_fields(model.Options)}")
    
    # # Check for badge attributes
    # badge_attrs = ['vision', 'allows_system_prompts', 'attachment_types', 'dimensions', 
    #                'truncate', 'supports_binary', 'supports_text', 'embed_batch']
    
    # print("Badge attributes:")
    # for attr in badge_attrs:
    #     if hasattr(model, attr):
    #         value = getattr(model, attr)
    #         print(f"  {attr}: {value} (type: {type(value)})")
    
    print("--------------------------------")

# Check embedding models too
print("\nEmbedding Models:")
embedding_models = llm.get_embedding_models()
for model in embedding_models:
    print(f'Name: {str(model)}')
    
    # # Check for badge attributes
    # badge_attrs = ['vision', 'allows_system_prompts', 'attachment_types', 'dimensions', 
    #                'truncate', 'supports_binary', 'supports_text', 'embed_batch']
    
    # print("Badge attributes:")
    # for attr in badge_attrs:
    #     if hasattr(model, attr):
    #         value = getattr(model, attr)
    #         print(f"  {attr}: {value} (type: {type(value)})")
    
    print("--------------------------------")


    
    



