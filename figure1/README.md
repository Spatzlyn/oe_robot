# Figure 1: saved 1920×1080 sensor example

Generate editable SVG, vector PDF and 300 dpi PNG from the saved records:

```bash
python figure1/build_figure.py --out results/figure1
```

Requires NumPy and Matplotlib, and no native environment, simulator or GPU.
The output directory must be new. The command does not rerender depth or run
the planner. It checks all input hashes and 93 assertions before exporting:

- `c1_1920_t3p5_original_vs_single_admission.{pdf,svg,png}`: same scene,
  observations, time and native execution prefix; one admission differs.
- `c1_1920_t4p0_original.{pdf,svg,png}`: the next observation epoch in Original.
- `membership.csv`, `whole_output_union.csv`, `all_output_segments.csv`,
  `scene_coordinates.json`: exact numerical coordinates and complete output.
- `same_prefix_and_intervention.json`: source depth hashes, intervention and
  the 482 matching events through the target admission observation.
- `witness_reference.json`, `audit.json`, `extraction_manifest.json`:
  independent feasibility, checks, drawing configuration and execution scope.

The checked-in `expected/` directory was regenerated using this public script.
`inputs/` contains the path-sanitized historical source records; the original
results, native source files, depth arrays, poses and intervention are unchanged.
`source_manifest.json` hashes the distributed input files. Historical harness
hashes are retained explicitly where sanitization changed the source bytes.

Blue segments represent the **position projection of the union of all
returned shadows**. Their stroke width is visual, not physical lateral extent.
The orange hatched outline and diamond represent an independently feasible
stationary body and reference position, not an observed/detected object.
At 3.5 s the reference position is absent from Original and present after
single admission. At 4.0 s Original regenerates it after another observation;
this does not cancel the preceding omission.

The figure measures no checker verdict, collision, or task completion and
must not be combined with the separate legacy checker experiment as one
end-to-end scene. The main figure is 7.15 inches wide with minimum 8 pt text;
the secondary figure is 3.5 inches wide with minimum 7.7 pt text. SVG text is
editable; PDF embeds TrueType fonts. Caption source: `figure_caption.tex`.
