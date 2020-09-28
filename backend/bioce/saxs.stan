data {
  int n_measures;
  int n_structures;
  vector[n_measures] target_curve;
  vector[n_measures] target_errors;
  matrix[n_measures, n_structures] sim_curves;
  vector[n_structures] priors;
}

parameters {
  simplex[n_structures] weights;
  real scale;
}

model {
  vector[n_structures] alphas;
  vector[n_measures] pred_curve;
  alphas = priors;
  weights ~ dirichlet(alphas);
  pred_curve = sim_curves * weights * scale;
  target_curve ~ normal(pred_curve, target_errors);
}