# ensemble_model class

from __future__ import absolute_import

import cobra
import random
import pandas as pd

class Ensemble:
    """
    Ensemble of metabolic models. Contains a base_model of type
    cobra.core.Model which consists of all reactions and genes
    present in any model within the ensemble. Also contains a
    reaction_diff of type dictionary which specifies reaction
    bounds for each model for every reaction that contains a difference
    in any model in the ensemble.

    reaction_diff: {ensemble_member_id:{reaction_id:{'ub':ub,'lb':lb}}}
    base_model: Cobra.core.Model object.
    """

    def __init__(self,base_id,model_list=None,join_method="concurrent",join_size=1):
        """
        Parameters
        ----------
        model_list: list of cobra.core.Model objects
            List of models to generate a single Ensemble object from.
        base_id: string
            identifier which will be assigned as the Ensemble's id.
        join_method: string
            Indicates the method used to construct the ensemble from model_list.
            Can be either "concurrent" or "iterative". Choose "concurrent" if
            the number of models is sufficiently small such that they can all be
            loaded into memory at the same time (not recommended for more than
            dozens of models with ~1000 reactions each). Otherwise, "iterative"
            will only load one model in memory at any given time; slower than
            "concurrent", but more memory efficient (required for large groups
            of large models).
        join_size: int
            Number of models to add to the ensemble during each iteration. Can
            only be used if join_method="iterative". Higher values consume more
            memory but should run more quickly. Default value is 1.
        """

        if join_method not in ["concurrent","iterative"]:
            raise ValueError("join_method must be either 'concurrent' or 'iterative'")

        self.features = pd.DataFrame()
        self.states = pd.DataFrame()
        if not model_list:
            self.base_model = cobra.core.Model(base_id+'_base_model')
            #self.reaction_diffs = {}
        else:

            if join_method == "concurrent":
                self.base_model = self._create_base_model(model_list,base_id=base_id+'_base_model')
                #self.reaction_diffs = self._create_reaction_diffs(model_list)
                set_features_states(self,model_list=model_list)
            elif join_method == "iterative":
                self.base_model = cobra.core.Model(base_id+'_base_model')
                set_features_states(self,model_list[0:join_size])
                remainder = len(model_list) % join_size
                steps = int(len(model_list)/join_size)
                for i in range(steps):
                    model_group = model_list[(i+1)*join_size:i+2*join_size]
                    #self.add_models(model_group)
                    update_features_states(self,model_group)
                if remainder > 0:
                    update_features_states(self,model_list[-1*remainder:])
                    #self.add_models(model_list[-1*remainder:])
        self.id=base_id


    # def add_models(self,model_list):
    #     '''
    #     Adds an additional model to an existing ensemble. Modifies base_model to
    #     include any unique reactions and updates the reaction diff.
    #
    #     When creating an ensemble for more than hundreds of models, creating an
    #     empty base model, then adding the models individually using add_models
    #     can prevent the need to load all models simultaneously (e.g. you can
    #     load and add one at a time, then clear the individual model from memory).
    #     This methods conserves memory relative to Ensemble_model.init, but may take
    #     slightly longer to run as the reaction diff is recalculated for each
    #     addition and more calls to base_model.add_reactions() are made.
    #
    #     WARNING: currently requires starting from an ensemble object which
    #     contains at least one base model. If an empty ensemble is used with
    #     add_models(), the diff is considered to be every reaction. We should
    #     refactor to enable starting with an empty model, since this makes
    #     code a little cleaner for the user.
    #     '''
    #
    #     if len(self.states) < 1:
    #         # If empty, just generate new base and diffs from input models
    #         new_base_model = self._create_base_model(model_list=model_list)
    #         #new_reaction_diffs = self._create_reaction_diffs(model_list=model_list)
    #         self.base_model = new_base_model
    #         set_features_states(model_list=model_list)
    #         #self.reaction_diffs = new_reaction_diffs
    #     else:
    #         new_base_model = self._create_base_model(model_list=model_list)
    #         new_reaction_diffs = self._create_reaction_diffs(model_list=model_list)
    #
    #         old_base_rxns = [rxn.id for rxn in self.base_model.reactions]
    #         new_base_rxns = [rxn.id for rxn in new_base_model.reactions]
    #         # currently grabs the reaction list from the first model. Requires update
    #         # if reaction_diff is refactored.
    #         old_diff_rxns = [rxn for rxn in self.reaction_diffs[list(self.reaction_diffs.keys())[0]]]
    #         new_diff_rxns = [rxn for rxn in new_reaction_diffs[list(new_reaction_diffs.keys())[0]]]
    #
    #         # find reactions in the new base that aren't in the old_base
    #         new_base_notin_old_base = list(set(new_base_rxns) - set(old_base_rxns)) # these should be in new diff
    #         # find reactions in the old base that aren't in the new base
    #         old_base_notin_new_base = list(set(old_base_rxns) - set(new_base_rxns)) # these should be in new diff
    #         # find reactions present in both new and old bases.
    #         in_both_bases = list(set(old_base_rxns) & set(new_base_rxns)) # these are the new universal reactions (if they have the same bounds)
    #
    #         rxns_to_add_to_old_base = []
    #         for reaction in new_base_notin_old_base:
    #             rxns_to_add_to_old_base.append(new_base_model.reactions.get_by_id(reaction))
    #             for model in self.reaction_diffs.keys():
    #                 # close the reaction in the old reaction diffs
    #                 self.reaction_diffs[model][reaction] = {'lb':0.0,'ub':0.0}
    #             if reaction not in new_diff_rxns:
    #                 # if the reaction wasn't in the new_diffs, we need to add it with
    #                 # the bounds from the new base since the reaction is absent from the old models
    #                 lb_in_new_base = new_base_model.reactions.get_by_id(reaction).lower_bound
    #                 ub_in_new_base = new_base_model.reactions.get_by_id(reaction).upper_bound
    #                 for model in new_reaction_diffs.keys():
    #                     new_reaction_diffs[model][reaction] = \
    #                         {'lb':lb_in_new_base,'ub':ub_in_new_base}
    #
    #         for reaction in old_base_notin_new_base:
    #             if reaction not in old_diff_rxns:
    #                 # if the reaction isn't in the old diff but isn't in the new base,
    #                 # we need to add it to the diff with
    #                 # the bounds from old_reaction_diff since it isn't in the new base.
    #                 # (e.g. the reaction is now different in some models)
    #                 lb_in_old_base = self.base_model.reactions.get_by_id(reaction).lower_bound
    #                 ub_in_old_base = self.base_model.reactions.get_by_id(reaction).upper_bound
    #                 for model in self.reaction_diffs.keys():
    #                     self.reaction_diffs[model][reaction] = \
    #                         {'lb':lb_in_old_base,'ub':ub_in_old_base}
    #                 # add the reaction to the new diffs, with it closed since it
    #                 # wasn't in the new base.
    #                 for model in new_reaction_diffs.keys():
    #                     new_reaction_diffs[model][reaction] = {'lb':0.0,'ub':0.0}
    #             else:
    #                 #if the reaction was in the old_diff, we must add it to new_diff since it's
    #                 # variable in a set of models
    #                 if not reaction in new_diff_rxns: # this should always be true since these reactions aren't in the new base, but just in case.
    #                     for model in new_reaction_diffs.keys():
    #                         new_reaction_diffs[model][reaction] = {'lb':0.0,'ub':0.0}
    #
    #         for reaction in in_both_bases:
    #             if reaction in old_diff_rxns:
    #                 if reaction not in new_diff_rxns:
    #                     # add to new diff with bounds from new_base
    #                     lb_in_new_base = new_base_model.reactions.get_by_id(reaction).lower_bound
    #                     ub_in_new_base = new_base_model.reactions.get_by_id(reaction).upper_bound
    #                     for model in new_reaction_diffs.keys():
    #                         new_reaction_diffs[model][reaction] = \
    #                             {'lb':lb_in_new_base,'ub':ub_in_new_base}
    #             if reaction in new_diff_rxns:
    #                 if reaction not in old_diff_rxns:
    #                     # add to old diff with bound from old_base
    #                     lb_in_old_base = self.base_model.reactions.get_by_id(reaction).lower_bound
    #                     ub_in_old_base = self.base_model.reactions.get_by_id(reaction).upper_bound
    #                     for model in self.reaction_diffs.keys():
    #                         self.reaction_diffs[model][reaction] = \
    #                             {'lb':lb_in_old_base,'ub':ub_in_old_base}
    #             else:
    #                 # if the reaction is in neither diff, check whether the bounds
    #                 # are the same in both old and new base, then update diffs
    #                 lb_in_new_base = new_base_model.reactions.get_by_id(reaction).lower_bound
    #                 ub_in_new_base = new_base_model.reactions.get_by_id(reaction).upper_bound
    #                 lb_in_old_base = self.base_model.reactions.get_by_id(reaction).lower_bound
    #                 ub_in_old_base = self.base_model.reactions.get_by_id(reaction).upper_bound
    #                 if lb_in_new_base != lb_in_old_base or ub_in_new_base != ub_in_old_base:
    #                     for model in self.reaction_diffs.keys():
    #                         self.reaction_diffs[model][reaction] = \
    #                             {'lb':lb_in_old_base,'ub':ub_in_old_base}
    #                     for model in new_reaction_diffs.keys():
    #                         new_reaction_diffs[model][reaction] = \
    #                             {'lb':lb_in_new_base,'ub':ub_in_new_base}
    #         # update the base_model and reaction_diff
    #         self.base_model.add_reactions(rxns_to_add_to_old_base)
    #         self.base_model.repair()
    #         for model in new_reaction_diffs.keys():
    #             self.reaction_diffs[model] = new_reaction_diffs[model]

    def _apply_state(self,model_id):
        '''
        Set the base model to the state for the given model_name. Used as a helper
        function to more easily utilize utility functions from cobra (e.g.
        single reaction/gene deletions).

        '''
        model_states = self.states.loc[model_id]
        for reaction in model_states.index:
            if model_states.loc[reaction]:
                rxn.lower_bound = self.features.loc[reaction,'lower_bound']
                rxn.upper_bound = self.features.loc[reaction,'upper_bound']
            else:
                rxn.lower_bound = 0
                rxn.upper_bound = 0

    def _create_base_model(self,model_list,base_id='ensemble base'):
        '''
        Creates a base model from a list of universal models. Base models
        contain all reactions present in a list of models.
        '''
        base_model = cobra.Model(base_id)
        for model in model_list:
            rxns_to_add = []
            for reaction in model.reactions:
                if reaction.id not in [rxn.id for rxn in base_model.reactions]:
                    rxns_to_add.append(reaction.copy())
            base_model.add_reactions(rxns_to_add)
            base_model.repair()

        return base_model

    def _update_features(self,new_ensemble):

        # get the features in the new ensemble base_model missing from the
        # current base_model
        old_base_rxns = [rxn.id for rxn in self.base_model.reactions]
        new_base_rxns = [rxn.id for rxn in new_ensemble.base_model.reactions]
        # find reactions in the new base that aren't in the old_base
        new_base_notin_old_base = list(set(new_base_rxns) - set(old_base_rxns))

        # find variable features in the new ensemble that weren't variable in
        # the old ensemble
        new_features = new_ensemble.features.index.tolist()
        old_features = self.features.index.tolist()
        new_features_notin_old_features = list(set(new_features) - set(old_features))

        features_to_add = list(set(new_base_notin_old_base) & set(new_features_notin_old_features))



    def _update_states(self,new_ensemble):
        'placeholder'

    def _update_base(self,new_ensemble):
        'placeholder'


def set_features_states(ensemble,model_list):
    """
    Sets the ensemble.features and ensemble.states dataframes given a list
    of input models. Used when creating a new ensemble. To update features
    and states of an existing ensemble when adding additional models, use
    _update_features_states.

    Parameters
    ----------
    model_list: list of cobra.core.Model objects
        List of models to generate a single Ensemble object from.
    """

    # if the model list is of length 1, there aren't any variable reactions.
    if len(model_list) == 1:
        ensemble.features = pd.DataFrame()
        ensemble.states = pd.DataFrame()
    else:
        # Get list of every reaction present in all models
        reaction_set = set()
        for model in model_list:
            model_reactions = set([reaction.id for reaction in model.reactions])
            if len(reaction_set) > 0:
                reaction_set = reaction_set & model_reactions
            else:
                reaction_set = model_reactions
        reaction_list = list(reaction_set)


        for model in model_list:
            variable_reactions = {}
            reactions_different = [rxn for rxn in model.reactions if rxn.id not in reaction_list]
            for reaction in reactions_different:
                if not reaction.id in variable_reactions.keys():
                    variable_reactions[reaction.id] = {'lower_bound':model.reactions.get_by_id(reaction.id).lower_bound,\
                                                        'upper_bound':model.reactions.get_by_id(reaction.id).upper_bound,\
                                                        'type':'reaction',\
                                                        'model_identifier':reaction.id}
            model_states = pd.DataFrame({feature:True for feature in variable_reactions.keys()},index=[model.id])
            features = pd.DataFrame(variable_reactions).T
            ### STILL NEED TO GET CORRECT FEATURE IDs BACK TO THE STATE DATAFRAME FOR REDUNDANT FEATURES

            if len(ensemble.features) > 0:
                new_df = pd.concat([ensemble.features,features])
                duplicate_features = new_df.duplicated()
                new_df = new_df[~duplicated_features] # remove true duplicates
                new_df.index = new_df.index + \
                            new_df.groupby('model_identifier').cumcount().astype(str) # add integer to index based on the feature being assigned to the
                            # same identifier within the model (e.g. same reaction id)
                ensemble.features = new_df
                new_df = pd.concat([ensemble.states,model_states])
                ensemble.states = new_df.fillna(False)
            else:
                ensemble.features = ensemble.features.join(features,how='outer')
            #self.features = self.features.join(features,how='outer')
                ensemble.states = ensemble.states.join(model_states,how='outer')

def update_features_states(current_ensemble,model_list):
    """
    Updates the ensemble.features and ensemble.states dataframes given a list
    of input models. Used when adding additional models to an ensemble. To
    set features and states for a new ensemble, use set_features_states.

    Parameters
    ----------
    model_list: list of cobra.core.Model objects
        List of models to add to this Ensemble object.
    """

    # create a new ensemble from the input list
    new_ensemble = Ensemble(base_id='new_models',model_list=model_list)
    current_ensemble._update_features(new_ensemble)
    current_ensemble._update_states(new_ensemble)
    current_ensemble._update_base(new_ensemble)

    # tasks:
    # 1. update base with new reactions
    # 2. add reactions to features that are now newly variable and update model states for new feature
    # 3.
    # determine reactions that need to be added to the diff (present in new ensemble and not in base)



    # merge the old ensemble with the new ensemble
    all_features = pd.concat([current_ensemble.features,new_ensemble.features])
    current_ensemble.features = all_features[~all_features.index.duplicated(keep='first')]
    all_states = pd.concat([current_ensemble.states,new_ensemble.states])
    current_ensemble.states = all_states.fillna(False)

def add_models(current_ensemble,model_list):
    '''
    Adds an additional model to an existing ensemble. Modifies base_model to
    include any unique reactions and updates the reaction diff.

    When creating an ensemble for more than hundreds of models, creating an
    empty base model, then adding the models individually using add_models
    can prevent the need to load all models simultaneously (e.g. you can
    load and add one at a time, then clear the individual model from memory).
    This methods conserves memory relative to Ensemble_model.init, but may take
    slightly longer to run as the reaction diff is recalculated for each
    addition and more calls to base_model.add_reactions() are made.

    WARNING: currently requires starting from an ensemble object which
    contains at least one base model. If an empty ensemble is used with
    add_models(), the diff is considered to be every reaction. We should
    refactor to enable starting with an empty model, since this makes
    code a little cleaner for the user.
    '''

    if len(current_ensemble.states) < 1:
        # If empty, just generate new base and diffs from input models
        new_base_model = current_ensemble._create_base_model(model_list=model_list)
        #new_reaction_diffs = self._create_reaction_diffs(model_list=model_list)
        current_ensemble.base_model = new_base_model
        set_features_states(current_ensemble,model_list=model_list)
        #self.reaction_diffs = new_reaction_diffs
    else:
        new_ensemble = Ensemble(model_list=model_list)
        #new_reaction_diffs = self._create_reaction_diffs(model_list=model_list)

        old_base_rxns = [rxn.id for rxn in current_ensemble.base_model.reactions]
        new_base_rxns = [rxn.id for rxn in new_ensemble.base_model.reactions]
        # currently grabs the reaction list from the first model. Requires update
        # if reaction_diff is refactored.
        old_features = old_ensemble.features.index.tolist()
        new_features = new_ensemble.features.index.tolist()

        # find reactions in the new base that aren't in the old_base
        new_base_notin_old_base = list(set(new_base_rxns) - set(old_base_rxns)) # these should be in new diff
        # find reactions in the old base that aren't in the new base
        old_base_notin_new_base = list(set(old_base_rxns) - set(new_base_rxns)) # these should be in new diff
        # find reactions present in both new and old bases.
        in_both_bases = list(set(old_base_rxns) & set(new_base_rxns)) # these are the new universal reactions (if they have the same bounds)

        rxns_to_add_to_old_base = []
        for reaction in new_base_notin_old_base:
            rxns_to_add_to_old_base.append(new_ensemble.base_model.reactions.get_by_id(reaction))
            for model in current_ensemble.states.index.tolist():
                # close the reaction in the old reaction diffs
                #self.reaction_diffs[model][reaction] = {'lb':0.0,'ub':0.0}
                current_ensemble.states.loc[model,reaction] = False
            if reaction not in new_features:
                # if the reaction wasn't in the new features, we need to add it with
                # the bounds from the new base since the reaction is absent from the old models
                lb_in_new_base = new_ensemble.base_model.reactions.get_by_id(reaction).lower_bound
                ub_in_new_base = new_ensemble.base_model.reactions.get_by_id(reaction).upper_bound
                for model in new_ensemble.states.index.tolist():
                    new_reaction_diffs[model][reaction] = \
                        {'lb':lb_in_new_base,'ub':ub_in_new_base}

        for reaction in old_base_notin_new_base:
            if reaction not in old_diff_rxns:
                # if the reaction isn't in the old diff but isn't in the new base,
                # we need to add it to the diff with
                # the bounds from old_reaction_diff since it isn't in the new base.
                # (e.g. the reaction is now different in some models)
                lb_in_old_base = self.base_model.reactions.get_by_id(reaction).lower_bound
                ub_in_old_base = self.base_model.reactions.get_by_id(reaction).upper_bound
                for model in self.reaction_diffs.keys():
                    self.reaction_diffs[model][reaction] = \
                        {'lb':lb_in_old_base,'ub':ub_in_old_base}
                # add the reaction to the new diffs, with it closed since it
                # wasn't in the new base.
                for model in new_reaction_diffs.keys():
                    new_reaction_diffs[model][reaction] = {'lb':0.0,'ub':0.0}
            else:
                #if the reaction was in the old_diff, we must add it to new_diff since it's
                # variable in a set of models
                if not reaction in new_diff_rxns: # this should always be true since these reactions aren't in the new base, but just in case.
                    for model in new_reaction_diffs.keys():
                        new_reaction_diffs[model][reaction] = {'lb':0.0,'ub':0.0}

        for reaction in in_both_bases:
            if reaction in old_diff_rxns:
                if reaction not in new_diff_rxns:
                    # add to new diff with bounds from new_base
                    lb_in_new_base = new_base_model.reactions.get_by_id(reaction).lower_bound
                    ub_in_new_base = new_base_model.reactions.get_by_id(reaction).upper_bound
                    for model in new_reaction_diffs.keys():
                        new_reaction_diffs[model][reaction] = \
                            {'lb':lb_in_new_base,'ub':ub_in_new_base}
            if reaction in new_diff_rxns:
                if reaction not in old_diff_rxns:
                    # add to old diff with bound from old_base
                    lb_in_old_base = self.base_model.reactions.get_by_id(reaction).lower_bound
                    ub_in_old_base = self.base_model.reactions.get_by_id(reaction).upper_bound
                    for model in self.reaction_diffs.keys():
                        self.reaction_diffs[model][reaction] = \
                            {'lb':lb_in_old_base,'ub':ub_in_old_base}
            else:
                # if the reaction is in neither diff, check whether the bounds
                # are the same in both old and new base, then update diffs
                lb_in_new_base = new_base_model.reactions.get_by_id(reaction).lower_bound
                ub_in_new_base = new_base_model.reactions.get_by_id(reaction).upper_bound
                lb_in_old_base = self.base_model.reactions.get_by_id(reaction).lower_bound
                ub_in_old_base = self.base_model.reactions.get_by_id(reaction).upper_bound
                if lb_in_new_base != lb_in_old_base or ub_in_new_base != ub_in_old_base:
                    for model in self.reaction_diffs.keys():
                        self.reaction_diffs[model][reaction] = \
                            {'lb':lb_in_old_base,'ub':ub_in_old_base}
                    for model in new_reaction_diffs.keys():
                        new_reaction_diffs[model][reaction] = \
                            {'lb':lb_in_new_base,'ub':ub_in_new_base}
        # update the base_model and reaction_diff
        self.base_model.add_reactions(rxns_to_add_to_old_base)
        self.base_model.repair()
        for model in new_reaction_diffs.keys():
            self.reaction_diffs[model] = new_reaction_diffs[model]
