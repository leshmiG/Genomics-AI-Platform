# Safety practices for clinical machine learning

## Discrimination and calibration
A model can rank patients well (high AUC) and still give misleading probabilities. Calibration measures whether a predicted 30 percent risk really corresponds to about 30 percent of such patients having the event. Report the Brier score and a calibration curve or expected calibration error, and recalibrate when the population changes. Choose decision thresholds using the costs of false positives and false negatives, not the default of 0.5.

## Subgroup performance and fairness
Evaluate performance separately by relevant groups, such as ancestry, sex, age band, and site. Allele frequencies differ between populations, and reference panels are historically skewed towards European ancestry, so a model or reference table built mostly on one population can underperform for others. Report subgroup sample sizes and confidence intervals, and document known gaps.

## Data leakage and validation
Split data by patient, not by row, so the same person never appears in both train and test sets. Keep a final held-out set for one-time evaluation, use time-based splits when the model will predict the future, and seek external validation at a different site before deployment.

## Drift monitoring
After deployment, monitor input drift (for example Population Stability Index per feature), prediction drift, and when labels arrive, performance drift. A PSI below 0.1 is usually treated as stable, 0.1 to 0.25 as a moderate shift to investigate, and above 0.25 as a significant shift. Define alert thresholds, an owner, and a rollback or retraining procedure.

## Model documentation and versioning
A model card records intended use, training data, metrics, subgroup results, limitations, and the software versions used. Every prediction response should include the model version so that a result can be traced and reproduced. Keep a model registry with approval status, and promote models through staging with a human sign-off.

## Human oversight
Clinical decision support should support, not replace, a clinician. Show the evidence and uncertainty, make it easy to override, and log overrides. Large language models must not make dosing or diagnostic decisions. Deterministic, validated logic should compute any clinical call, and the language model should only explain it and answer questions grounded in cited sources.

## Regulation
Software that influences diagnosis or treatment may be regulated as a medical device (for example SaMD under FDA or EU MDR rules). Early engagement with the regulatory team is needed to decide the intended-use statement and the quality system required.
