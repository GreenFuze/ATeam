from typing import Dict, Any, List

class ConfigMerger:
    def merge_scalars(self, values: List[Any]) -> Any:
        """Return first non-None value (highest priority wins)."""
        for value in values:
            if value is not None:
                return value
        return None

    def merge_dicts(self, dicts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Deep merge dictionaries (higher overrides keys)."""
        if not dicts:
            return {}
        
        result = dicts[0].copy()  # Start with highest priority
        
        for d in dicts[1:]:  # Merge lower priority dicts
            if d:
                self._deep_merge(result, d)
        
        return result

    def merge_lists(self, lists: List[List[Any]], key: str = "") -> List[Any]:
        """If key given, de-dupe by that item key; else naive de-dupe by value."""
        if not lists:
            return []
        
        # Concatenate all lists (highest priority first)
        combined = []
        for lst in lists:
            if lst:
                combined.extend(lst)
        
        if not key:
            # Naive de-dupe by value
            seen = set()
            result = []
            for item in combined:
                if item not in seen:
                    seen.add(item)
                    result.append(item)
            return result
        else:
            # De-dupe by key
            seen = set()
            result = []
            for item in combined:
                if isinstance(item, dict) and key in item:
                    item_key = item[key]
                    if item_key not in seen:
                        seen.add(item_key)
                        result.append(item)
                else:
                    result.append(item)
            return result

    def _deep_merge(self, target: Dict[str, Any], source: Dict[str, Any]) -> None:
        """Recursively merge source into target."""
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._deep_merge(target[key], value)
            else:
                target[key] = value
