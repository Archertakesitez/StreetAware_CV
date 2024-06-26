import pandas as pd
import pickle
import xgboost
import shap
import numpy as np
from imblearn.over_sampling import SMOTE
from sklearn.model_selection import train_test_split
from collections import Counter
import os
from sklearn.metrics import accuracy_score, f1_score, confusion_matrix, roc_auc_score, roc_curve
import matplotlib.pyplot as plt
import seaborn as sns

#tested!
def make_classifier_test(csv_path = "data_feature.csv")->None:
    """
    This function train XGBoost classifier on csv feature data and load the model
    and X train dataset

    Args:
        csv_path: the path of csv that contains features of boxes
    """
    df = pd.read_csv(csv_path)
    df.drop(df.columns[0], axis=1, inplace=True)
    directory = os.getcwd()+"/"
    save_path_model = directory+"pretrained_tools/pretrained_xgboost.pkl"
    save_path_x_train = directory+"pretrained_tools/X_train.pkl"
    X, y = df.drop(labels=['frame','cls'],axis=1), df['cls']
    """
    #resample to boost tracking failure samples
    oversample = SMOTE()
    X, y = oversample.fit_resample(X, y)
    """
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    model = xgboost.XGBClassifier(scale_pos_weight = 10)
    model.fit(X_train, y_train)

    with open(save_path_model, 'wb') as f:
        pickle.dump(model, f)
    with open(save_path_x_train, 'wb') as f:
        pickle.dump(X, f)

    preds = model.predict(X_test)
    probs = model.predict_proba(X_test)[:, 1]
    # Compute the confusion matrix
    conf_matrix = confusion_matrix(y_test, preds)
    auc = roc_auc_score(y_test, probs)
    print(conf_matrix)
    print("Accuracy:", accuracy_score(y_test, preds))
    print("F1 Score:", f1_score(y_test, preds))
    print("AUC:",auc)
    """
    # ROC Curve
    fpr, tpr, thresholds = roc_curve(y_test, probs)
    plt.plot(fpr, tpr, color='darkorange', label=f'ROC curve (area = {auc:.2f})')
    plt.plot([0, 1], [0, 1], color='navy', linestyle='--')
    plt.xlabel('False Positive Rate')
    plt.ylabel('True Positive Rate')
    plt.title('Receiver Operating Characteristic')
    plt.legend(loc="lower right")
    plt.show()
    """
    # Set up the matplotlib figure and axes
    fig, ax = plt.subplots(1, 2, figsize=(12, 5))

    # Plot non-normalized confusion matrix
    plot_confusion_matrix(conf_matrix, classes=['Negative', 'Positive'], subplot=ax[0], normalize=False)

    # Plot normalized confusion matrix
    plot_confusion_matrix(conf_matrix, classes=['Negative', 'Positive'], subplot=ax[1], normalize=True)

    plt.tight_layout()
    plt.show()


# Function to plot confusion matrix
def plot_confusion_matrix(cm, classes, subplot, normalize=False, title='Confusion matrix', cmap=plt.cm.Blues):
    """
    This function plots the confusion matrix on a specified subplot axis.
    Normalization can be applied by setting `normalize=True`.
    """
    if normalize:
        cm = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]
        subplot.set_title('Normalized ' + title)
    else:
        subplot.set_title('Non-Normalized ' + title)

    sns.heatmap(cm, ax=subplot, annot=True, fmt=".2f" if normalize else "d", cmap=cmap, cbar=True, square=True)
    subplot.set_xlabel('Predicted labels')
    subplot.set_ylabel('True labels')
    subplot.set_xticklabels(classes)
    subplot.set_yticklabels(classes)
    #subplot.set_yticks(np.arange(len(classes))+0.5, rotation=0, va="center")



#tested!
def make_classifier_custom(df:pd.DataFrame)->None:
    """
    This function trains XGBoost classifier on custom pd dataframe and load the model and X train dataset

    Args:
        df: the pandas dataframe with labeled features. provided by user.
    """
    directory = os.getcwd()+"/"
    save_path_model = directory+"pretrained_tools/pretrained_xgboost_cus.pkl"
    save_path_x_train = directory+"pretrained_tools/X_train_cus.pkl"
    X, y = df.drop(labels=['frame','cls'],axis=1, inplace=False), df['cls']
    print(Counter(y))
    model = xgboost.XGBClassifier(scale_pos_weight = 10)
    model.fit(X, y)
    with open(save_path_model, 'wb') as f:
        pickle.dump(model, f)
    with open(save_path_x_train, 'wb') as f:
        pickle.dump(X, f)


#tested!
def output_df(df:pd.DataFrame)->pd.DataFrame:
    """
    This function output a dataframe that appends the inter_objects_occlusion column

    Args:
        csv_path: the string denoting the path of csv file which contains the features of boxes
    
    Returns:
        pd.DataFrame: a pandas df that includes the occlusion column
    """
    occlusion_list = []#for appending occlusion data for all frames
    for frame in df['frame'].unique():
        #for each frame
        new_df = df[df['frame']==frame].copy()
        curr_list = [0]*len(new_df)
        if len(new_df)==1:#if this frame just have a single box, there cannot be occlusion
            occlusion_list.extend(curr_list)#hence append a single 0 to the list
            break
        #when there are multiple boxes:
        for i in range(0,len(new_df)-1):
            for j in range(i+1,len(new_df)):
                if i!=j:
                    if if_occlusion(df=new_df,i=i,j=j):
                        curr_list[i] += 1
                        curr_list[j] += 1
        occlusion_list.extend(curr_list)
    df['inter_objects_occlusion'] = occlusion_list
    return df
#tested!
def if_occlusion(df: pd.DataFrame,i:int,j:int)->bool:
    """
    This function check if there two boxes in a frame appears to be occluded with each other

    Args:
        df: the truncated dataframe for a specific frame
        i: index for one row
        j: index for another row

    Return:
        bool: whether the ith row and jth row in df is occluded with each other
    """
    x_min_1 = df.iloc[i]['xmin']
    x_min_2 = df.iloc[j]['xmin']
    x_max_1 = df.iloc[i]['xmax']
    x_max_2 = df.iloc[j]['xmax']
    y_min_1 = df.iloc[i]['xmin']
    y_min_2 = df.iloc[j]['ymin']
    y_max_1 = df.iloc[i]['ymax']
    y_max_2 = df.iloc[j]['ymax']
    if (x_min_2>x_min_1 and x_min_2<x_max_1) or (x_max_2<x_max_1 and x_max_2>x_min_1):
        #when j's left side is inbetween i's width or when j's right side is inbetween i's width
        if (y_min_2<y_max_1 and y_min_2>y_min_1) or (y_max_2>y_min_1 and y_max_2<y_max_1):
            #when j's up side is inbetween i's height or when j's down side is inbetween i's height
            return True
    return False

