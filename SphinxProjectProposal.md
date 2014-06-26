{\rtf1\ansi\ansicpg1252\cocoartf1265\cocoasubrtf190
{\fonttbl\f0\fswiss\fcharset0 Helvetica;}
{\colortbl;\red255\green255\blue255;}
\margl1440\margr1440\vieww10800\viewh8400\viewkind0
\pard\tx720\tx1440\tx2160\tx2880\tx3600\tx4320\tx5040\tx5760\tx6480\tx7200\tx7920\tx8640\pardirnatural

\f0\fs24 \cf0 \
##Team Name: Sphinx Whitespace Project##\
\
_By: Jeremy Curtis, Nick Giranda, and Zafar Siddiqui_\
_____________________________________________________________\
\
###What is Sphinx?\
\
Sphinx is an open source documentation builder. The way it works is it takes in a directory of a reStructuredText source files, and it arranges them in a very nicely organized manner into HTML or PDF files for easy browsing. It allows a user to arrange the individual source files in a hierarchical structure with automatic indexing. \
\
###What needs to be changed?\
\
Sphinx seems to have an issue with whitespace.  When users publish their documents using Sphinx to HTML and PDF, referenced computer code is given an automatic whitespace lead when numbered lines are present.  While some users may prefer this leading whitespace, it is our team\'92s hope to complete the following.  First, locate the documentation/code that contains this issue.  Second, familiarize ourselves with Python in order to not only remove the automatic leading whitespace, but also to then add an option for the user that allows them to choose what whitespace level, if any, they would like in their exported documents.  Third, and finally, we plan to share this code/patch/addition to the  Sphinx FOSS in the hopes that maybe they will accept these updates for the benefit of all users.  In the least, our goal is to successfully investigate and correct (with options) this issue, brought to our attention by Sphinx user George Thiruvathukal.  Another resource, Dr. Robert yacobellis, a user of Sphinx, may also be looped into the issue and requested to share his ideas and input; Curtis will contact Robert.\
\
###Team Members and Tasks\
\
Our team, \'93Sphinx Whitespace Project,\'94 consists of three members.  Nick Giranda will focus on understanding then liaising with Sphinx, which may lead to figuring out the issue quicker.  Nick will also ensure that our updates work correctly, and will then propose these changes to Sphinx.  Curtis Main will coordinate communication, meetings, deadlines, responsibilities, and workflow, in addition to finding and sharing resources related to Python tutorials/training/code and Python compilers for team members.  Zafar Siddiqui will determine exactly where the issue is within the Sphinx coding/documentation that automatically causes whitespace.  Once determined, Zafar will report to the team and all members will work together in Python code to determine the best approaches to meeting our goal.\
\
\
\
While we have experience in coding, each will need to learn more about both Sphinx and Python.  We plan to utilize our previous experience in C sharp and other languages to work in Python.  Fortunately, our current and previous Loyola faculty/professors in the computer science department have created content and materials in both Python and Sphinx, thus, we plan to take advantage of their expertise and reach out to them during this project.\
\
###How will we proceed?\
\
As for the coding, our early conversations, having not yet pinpointed the exact issue causing the automatic whitespace, revolve around trimming.  Or, if code exists in Sphinx that specifies whitespace, we will remove this code.  We hope to offer the Sphinx user whitespace options.  it is our understanding that our coding options will come to us as we work through Sphinx and Python, \
\
Our first step will be to determine a compiler/editor to edit Python in.  Since some of our group has used Idle, we believe this might be a viable option.  Next, we plan on downloading Sphinx and attempting to replicate the bug.  From there, we will use the compiler/editor to read through the code and try to understand how the program accomplishes its task.  To assist us with this, we also plan to go through a few tutorials on Python to teach/reacquaint the group with the language.  Hopefully in doing so we will be able to pinpoint the source of the bug.  Once that has been accomplished, we will discuss options for fixing the bug and improving upon the software (adding options for whitespace with regards to imported code, etc.).\
\
Our team has found that the Sphinx project was hosted on Bitbucket.  While Bitbucket support both git and mercurial projects, and Sphinx appears to be a mercurial project.  Zafar was able to convert the project to git and upload it to a new Github repo.  This allows us to use Github, which is the standard for the class, but seems like it may defeat the point of using version control.  Also, we are wondering if this would make it harder to submit a pull request once we\'92ve completed our task?  We are currently awaiting George\'92s advice in using Github or Bitbucket.\
\
###Communication\
\
Regarding communication and meeting, we plan to convene as a group three times per week using Skype video and screen share chat, Tuesdays, Thursdays, and Sundays from 7-8 pm.  Between these times, we will communicate via Outlook and Google docs.  Per our project guidelines, we will also work through Bitbucket and Trello.  Also, we will work through Ubuntu in the virtual machine to install the Sphinx package and work with it. This way, we all will be working on the same platform to avoid possible confusions. \
\
###General Outline for the Course\
* Week 1 :	Course Introduction and repository and software installation/setup\
* Week 2:	Project research, selection, and team formation\
* Week 3:	Proposal and video share\
* Week 4: 	Python training/tutorials and Sphinx outreach\
* Week 5: 	Pinpoint documentation/code in Sphinx\
* Week 6:	Research/brainstorm options and solutions; each team member can explore ideas on their own then report back to the group\
* Week 7:	Work toward successful update/code; we might share code with George since he \
is the user who requested the fix\
* Week 8:	Project completion, presentation, and proposal to Sphinx\
\
\
\
}