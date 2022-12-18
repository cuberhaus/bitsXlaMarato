# bitsXlaMarato
By: Pol Casacuberta, Tatiana Meyer, Pablo Vega, Ton Vilà

## Inspiration
We were very inclined to work in this project because we thought we could solve the problem presented with our knowledge. Also, we were very excited to put ourselves into learning some new technologies and experiencing a Hackathon.

## What it does
This program converts an ecography into several frames to then detect the abdominal aorta. When it is located, we generate a 3D model and determine if the patient suffers from an aneurism by automatically calculating the diameter of the maximum point of the aorta.
All of this is ready to be used by a GUI we built. The detected aorta can be seen in a red color and a 3D model is generated, which can be rotated as desired. Also, a video is generated with the marked aorta.

## How we built it
We used the MaskRCNN Artificial Intelligence with some hand-made markups of some of the patients. This resulted in a trained model that we then applied to detect the aorta in other patients.
We then programmed a script to generate a 3D model of the aorta found in the pictures so we could see more clearly the aneurism in case it was present.

## Challenges we ran into
Firstly, using a AI its always a bit challenging, but in this case we could make it work. Also, time is a very big factor of every Hackathon, but in this case we consider we were very efficient as a group.

## Accomplishments that we're proud of
We are proud of finishing on time and delivering a product that the challengers will find useful to further investigate into AAA.

## What we learned
A lot of Python and how to use a AI. Before we did not know a lot about marking images and we were a bit worried it would not work after investing so much time into it.

## What's next for Aneurism detection with MarkRCNN
We are giving the challengers the trained model, which they can reuse. This would prove useful if they mark the frames of the ecographies, because even though we asked for help, they are professionals and can read an ecography proficiently.
Also, we are giving them a GUI and all the scripts used for the application.
