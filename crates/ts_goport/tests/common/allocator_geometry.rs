//! Failure-only allocator mapping facts. Absolute addresses never enter the result.
#[derive(Debug, Default, PartialEq, Eq)]
pub struct MappingFacts {
    pub length: usize,
    pub start_residue: usize,
    pub allocation_offset: usize,
}

#[derive(Debug, Default, PartialEq, Eq)]
pub struct Geometry {
    pub current: Option<MappingFacts>,
    pub previous: Option<MappingFacts>,
    pub same_mapping: Option<bool>,
}

#[must_use]
pub fn describe(maps: &str, current: usize, previous: Option<usize>, boundary: usize) -> Geometry {
    if boundary == 0 {
        return Geometry::default();
    }
    let mut result = Geometry::default();
    let mut current_region = None;
    let mut previous_region = None;
    for line in maps.lines() {
        let Some(range) = line.split_whitespace().next() else {
            continue;
        };
        let Some((start, end)) = range.split_once('-') else {
            continue;
        };
        let (Ok(start), Ok(end)) = (
            usize::from_str_radix(start, 16),
            usize::from_str_radix(end, 16),
        ) else {
            continue;
        };
        let Some(length) = end.checked_sub(start).filter(|length| *length > 0) else {
            continue;
        };
        if result.current.is_none() && (start..end).contains(&current) {
            result.current = Some(MappingFacts {
                length,
                start_residue: start % boundary,
                allocation_offset: current - start,
            });
            current_region = Some((start, end));
        }
        if let Some(previous) = previous
            && result.previous.is_none()
            && (start..end).contains(&previous)
        {
            result.previous = Some(MappingFacts {
                length,
                start_residue: start % boundary,
                allocation_offset: previous - start,
            });
            previous_region = Some((start, end));
        }
    }
    result.same_mapping = current_region
        .zip(previous_region)
        .map(|(current, previous)| current == previous);
    result
}

/// Only the selected documented sysfs policy crosses the logging boundary.
#[must_use]
pub fn thp_policy(source: &str) -> Option<&'static str> {
    let mut selected = source.split_whitespace().filter_map(|word| match word {
        "[always]" => Some("always"),
        "[madvise]" => Some("madvise"),
        "[never]" => Some("never"),
        _ => None,
    });
    let policy = selected.next()?;
    selected.next().is_none().then_some(policy)
}

#[cfg(test)]
mod tests {
    use super::*;

    const BOUNDARY: usize = 0x0020_0000;
    const BASE: usize = 0x1000_0000;
    const LENGTH: usize = 4 * BOUNDARY;
    const OFFSET: usize = 0x10000;

    #[test]
    fn selected_policy_is_closed_and_ambiguous_policy_is_unknown() {
        assert_eq!(thp_policy("always [madvise] never"), Some("madvise"));
        assert_eq!(thp_policy("[always] madvise never"), Some("always"));
        assert_eq!(thp_policy("always madvise [never]"), Some("never"));
        assert_eq!(thp_policy("[always] [never]"), None);
        assert_eq!(thp_policy("[unknown] private-marker"), None);
        assert_eq!(thp_policy(""), None);
    }

    fn maps() -> String {
        format!("{BASE:x}-{:x} rw-p 00000000 00:00 0\n", BASE + LENGTH)
    }

    #[test]
    fn reused_fragment_is_in_the_same_mapping() {
        let facts = describe(
            &maps(),
            BASE + BOUNDARY + OFFSET,
            Some(BASE + OFFSET),
            BOUNDARY,
        );
        assert_eq!(facts.same_mapping, Some(true));
        assert_eq!(
            facts.current,
            Some(MappingFacts {
                length: LENGTH,
                start_residue: 0,
                allocation_offset: BOUNDARY + OFFSET,
            })
        );
        assert_eq!(facts.previous.unwrap().allocation_offset, OFFSET);
    }

    #[test]
    fn distinct_mapping_is_not_contiguous_reuse() {
        let second = BASE + 2 * LENGTH;
        let maps = format!(
            "{}{second:x}-{:x} rw-p 0 00:00 0\n",
            maps(),
            second + LENGTH
        );
        let facts = describe(&maps, second + OFFSET, Some(BASE + OFFSET), BOUNDARY);
        assert_eq!(facts.same_mapping, Some(false));
        assert_eq!(facts.current.unwrap().allocation_offset, OFFSET);
        assert!(facts.previous.is_some());
    }

    #[test]
    fn malformed_overflow_empty_and_unknown_regions_are_absent() {
        for maps in [
            "",
            "not-a-range rw-p",
            "ffffffffffFFFFFFFFFFFFFFFF-1 rw-p",
            "20-10 rw-p",
            "10-10 rw-p",
        ] {
            assert_eq!(describe(maps, BASE, None, BOUNDARY), Geometry::default());
        }
        assert_eq!(
            describe(&maps(), BASE + LENGTH, None, BOUNDARY),
            Geometry::default()
        );
        assert_eq!(describe(&maps(), BASE, None, 0), Geometry::default());
    }

    #[test]
    fn missing_previous_mapping_remains_unknown() {
        let facts = describe(&maps(), BASE + OFFSET, Some(BASE - OFFSET), BOUNDARY);
        assert!(facts.current.is_some());
        assert!(facts.previous.is_none());
        assert_eq!(facts.same_mapping, None);
    }

    #[test]
    fn reports_only_geometry_without_address_or_mapping_payload() {
        let maps = format!("{}private-marker-path", maps());
        let facts = describe(&maps, BASE + OFFSET, None, BOUNDARY);
        let printed = format!("{facts:?}");
        assert!(facts.current.is_some());
        assert!(!printed.contains(&BASE.to_string()));
        assert!(!printed.contains("private-marker-path"));
        assert!(!printed.contains("10000000"));
    }
}
